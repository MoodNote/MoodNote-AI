"""
Prompt templates for synthetic diary generation and cross-LLM auditing.

Label meanings are anchored with short Vietnamese descriptions of the 7 UIT-VSMEC labels.
VSMEC sentences are deliberately NOT used as few-shot examples: they are social-media posts,
not diary entries, and the VSMEC test set must stay unseen by the generators.

Every prompt revision (after a prompt trial or a failed QA round) gets a new template id and
old templates are never edited in place, so each generated row, which records its
template_id, can be traced back to the exact prompt and label descriptions.
"""

import json
import re

from ...utils.emotion_constants import DEFAULT_EMOTION_LABELS, find_label_index_by_name

# (Vietnamese name, meaning) per label; keys match DEFAULT_EMOTION_LABELS values.
_DESCRIPTIONS_V1: dict[str, tuple[str, str]] = {
    "Enjoyment": ("vui vẻ", "niềm vui, hạnh phúc, hài lòng, thích thú, biết ơn hoặc tự hào"),
    "Sadness": ("buồn bã", "nỗi buồn, thất vọng, cô đơn, tiếc nuối, tủi thân hoặc chán nản"),
    "Anger": ("tức giận", "giận dữ, bực bội, cáu gắt hoặc ấm ức vì bị đối xử bất công"),
    "Fear": ("sợ hãi", "nỗi sợ, lo lắng, bất an hoặc hoảng hốt trước điều có thể xảy ra"),
    "Disgust": ("ghê tởm", "cảm giác ghê tởm, khinh bỉ hoặc chán ghét một hành vi, sự việc"),
    "Surprise": ("ngạc nhiên", "sự bất ngờ, ngỡ ngàng, sửng sốt trước điều không lường trước"),
    "Other": (
        "trung tính",
        "không thể hiện rõ cảm xúc nào trong 6 cảm xúc còn lại, chỉ kể lại sự việc bình thường",
    ),
}

# v2, after the v1 prompt trial: Disgust read as annoyance and Other drifted into Enjoyment,
# so both get sharper boundaries; "biết ơn" is dropped from Enjoyment (overused in the trial).
_DESCRIPTIONS_V2: dict[str, tuple[str, str]] = {
    **_DESCRIPTIONS_V1,
    "Enjoyment": ("vui vẻ", "niềm vui, hạnh phúc, hài lòng, thích thú hoặc tự hào"),
    "Disgust": (
        "ghê tởm",
        "cảm giác ghê tởm, kinh tởm, buồn nôn hoặc khinh bỉ trước một hành vi, sự việc bẩn thỉu "
        "hay đồi bại, khác với bực bội hay tức giận",
    ),
    "Other": (
        "trung tính",
        "không vui cũng không buồn, không thể hiện rõ cảm xúc nào trong 6 cảm xúc còn lại; giọng "
        "kể trung tính về sự việc bình thường",
    ),
}

# v3, after the v2 trial: both models copied "không vui cũng không buồn" from the Other
# description into their Other entries, a lexical shortcut PhoBERT would learn instead of the
# label. Other goes back to a v1-style description without a quotable emotion phrase.
_DESCRIPTIONS_V3: dict[str, tuple[str, str]] = {
    **_DESCRIPTIONS_V2,
    "Other": (
        "trung tính",
        "không thể hiện rõ cảm xúc nào trong 6 cảm xúc còn lại, chỉ kể lại sự việc thường ngày",
    ),
}

# v4, after the v3 cross-LLM audit (label mismatch 21.9% against a 15% gate): Other entries
# slipped in mild pleasure or gloom (Qwen 78% mismatch), Anger entries described being hurt and
# were read as Sadness, and Surprise/Fear were pulled toward the valence of the event. The four
# descriptions now state what the emotion is aimed at and where it ends.
_DESCRIPTIONS_V4: dict[str, tuple[str, str]] = {
    **_DESCRIPTIONS_V3,
    "Anger": (
        "tức giận",
        "giận dữ, bực bội, cáu gắt hoặc phẫn nộ với người hay việc gây ra điều sai trái, muốn "
        "phản ứng, lên tiếng hoặc trách móc; khác với buồn hay tủi thân vì bị tổn thương",
    ),
    "Fear": (
        "sợ hãi",
        "nỗi sợ, lo lắng, bất an hoặc hoảng hốt trước một mối nguy hay điều xấu có thể sắp xảy "
        "ra; khác với nỗi buồn về điều đã mất",
    ),
    "Surprise": (
        "ngạc nhiên",
        "sự bất ngờ, ngỡ ngàng, sửng sốt trước điều không lường trước; cảm giác bất ngờ là chính, "
        "không để niềm vui hay nỗi buồn về sự việc lấn át",
    ),
    "Other": (
        "trung tính",
        "không thể hiện rõ cảm xúc nào trong 6 cảm xúc còn lại, chỉ kể lại sự việc thường ngày; "
        "không kèm lời khen chê, cảm nhận dễ chịu hay khó chịu, hay suy ngẫm rút ra bài học",
    ),
}

# template id -> (system prompt, user prompt, label descriptions). The user prompt takes
# {label_vi} {description} {van_phong} {do_dai} {ngu_canh} placeholders.
GENERATION_TEMPLATES: dict[str, tuple[str, str, dict[str, tuple[str, str]]]] = {
    "diary_v1": (
        "Bạn là một người Việt Nam đang viết nhật ký cá nhân của chính mình.",
        "Hãy viết một đoạn nhật ký bằng tiếng Việt.\n"
        "\n"
        "Yêu cầu:\n"
        "- Viết ở ngôi thứ nhất, giọng văn nhật ký cá nhân đời thường, như đang viết cho chính "
        "mình đọc. Đây KHÔNG phải bài đăng mạng xã hội: không hashtag, không emoji, không nhắn "
        "gửi người đọc.\n"
        "- Cảm xúc chủ đạo: {label_vi} ({description}).\n"
        "- Văn phong: {van_phong}.\n"
        "- Độ dài: {do_dai}.\n"
        "- Ngữ cảnh: {ngu_canh}.\n"
        "- Chỉ trả về nội dung đoạn nhật ký, không tiêu đề, không giải thích hay bình luận thêm.",
        _DESCRIPTIONS_V1,
    ),
    # v1 trial: Llama mixed in English/Chinese and ignored the style/length axes; some axis
    # combinations (e.g. Anger x "thành công nhỏ") pulled the text off its label; both models
    # named the emotion outright. v2 asks for Vietnamese only, a concrete situation in the
    # context that fits the emotion, the emotion shown rather than named, and pronouns/wording
    # matching the style.
    "diary_v2": (
        "Bạn là một người Việt Nam đang viết nhật ký cá nhân của chính mình.",
        "Hãy viết một đoạn nhật ký bằng tiếng Việt.\n"
        "\n"
        "Yêu cầu:\n"
        "- Viết ở ngôi thứ nhất, giọng văn nhật ký cá nhân đời thường, như đang viết cho chính "
        "mình đọc. Đây KHÔNG phải bài đăng mạng xã hội: không hashtag, không emoji, không nhắn "
        "gửi người đọc, không kết thúc bằng lời chào như viết thư.\n"
        "- Chỉ dùng tiếng Việt, không chèn từ hay câu tiếng Anh, tiếng Trung.\n"
        "- Cảm xúc chủ đạo: {label_vi} ({description}).\n"
        '- Hãy nghĩ ra một tình huống cụ thể thuộc ngữ cảnh "{ngu_canh}" phù hợp với cảm xúc '
        "chủ đạo trên.\n"
        "- Thể hiện cảm xúc qua sự việc, suy nghĩ và phản ứng của người viết; hạn chế gọi thẳng "
        "tên cảm xúc.\n"
        "- Văn phong: {van_phong}. Cách xưng hô và dùng từ phải khớp với văn phong này.\n"
        "- Độ dài: {do_dai}.\n"
        "- Chỉ trả về nội dung đoạn nhật ký, không tiêu đề, không giải thích hay bình luận thêm.",
        _DESCRIPTIONS_V2,
    ),
    # v2 trial: Qwen followed every axis; Llama 3 still named the emotion and copied words from
    # the label description (e.g. the Anger synonyms verbatim). v3 also forbids summarising
    # one's own feeling and reusing the description's wording. The same round switched the
    # generator to Llama 3.1 and neutralised two emotion-laden contexts (datagen_config.yaml).
    "diary_v3": (
        "Bạn là một người Việt Nam đang viết nhật ký cá nhân của chính mình.",
        "Hãy viết một đoạn nhật ký bằng tiếng Việt.\n"
        "\n"
        "Yêu cầu:\n"
        "- Viết ở ngôi thứ nhất, giọng văn nhật ký cá nhân đời thường, như đang viết cho chính "
        "mình đọc. Đây KHÔNG phải bài đăng mạng xã hội: không hashtag, không emoji, không nhắn "
        "gửi người đọc, không kết thúc bằng lời chào như viết thư.\n"
        "- Chỉ dùng tiếng Việt, không chèn từ hay câu tiếng Anh, tiếng Trung.\n"
        "- Cảm xúc chủ đạo: {label_vi} ({description}).\n"
        '- Hãy nghĩ ra một tình huống cụ thể thuộc ngữ cảnh "{ngu_canh}" phù hợp với cảm xúc '
        "chủ đạo trên.\n"
        "- Thể hiện cảm xúc qua sự việc, suy nghĩ và phản ứng của người viết; hạn chế gọi thẳng "
        "tên cảm xúc hoặc tự tổng kết cảm xúc của mình, và không lặp lại nguyên văn các từ trong "
        "phần mô tả cảm xúc ở trên.\n"
        "- Văn phong: {van_phong}. Cách xưng hô và dùng từ phải khớp với văn phong này.\n"
        "- Độ dài: {do_dai}.\n"
        "- Chỉ trả về nội dung đoạn nhật ký, không tiêu đề, không giải thích hay bình luận thêm.",
        _DESCRIPTIONS_V3,
    ),
}
# v4 keeps the v3 wording and only swaps in the v4 label descriptions.
GENERATION_TEMPLATES["diary_v4"] = (
    GENERATION_TEMPLATES["diary_v3"][0],
    GENERATION_TEMPLATES["diary_v3"][1],
    _DESCRIPTIONS_V4,
)
assert all(
    set(descriptions) == set(DEFAULT_EMOTION_LABELS.values())
    for _, _, descriptions in GENERATION_TEMPLATES.values()
)

AUDIT_SYSTEM_PROMPT = "Bạn là người kiểm định dữ liệu cảm xúc tiếng Việt."

AUDIT_USER_TEMPLATE = (
    "Đọc đoạn nhật ký dưới đây và trả lời 2 câu hỏi.\n"
    "\n"
    'Đoạn nhật ký:\n"""\n{text}\n"""\n'
    "\n"
    "1. Cảm xúc chủ đạo của đoạn nhật ký là nhãn nào trong 7 nhãn sau?\n"
    "{label_list}\n"
    "2. Đoạn nhật ký có tự nhiên như do người thật viết không? Trả lời false nếu văn phong "
    "rập khuôn, máy móc, thiếu tự nhiên hoặc lẫn từ, câu tiếng nước ngoài.\n"
    "\n"
    "Chỉ trả lời đúng một dòng JSON, không giải thích:\n"
    '{{"label": "<một trong 7 nhãn>", "natural": true hoặc false}}'
)

_JSON_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)


def build_generation_messages(
    template_id: str, label: str, van_phong: str, do_dai: str, ngu_canh: str
) -> list[dict[str, str]]:
    """
    Build the chat messages asking for one diary entry with the given emotion and axes.

    Args:
        template_id: Key of GENERATION_TEMPLATES
        label: Emotion label name (e.g. "Enjoyment")
        van_phong: Writing-style axis value
        do_dai: Length axis value
        ngu_canh: Context axis value

    Returns:
        Chat messages (system + user)
    """
    system, user, descriptions = GENERATION_TEMPLATES[template_id]
    label_vi, description = descriptions[label]
    content = user.format(
        label_vi=label_vi,
        description=description,
        van_phong=van_phong,
        do_dai=do_dai,
        ngu_canh=ngu_canh,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def build_audit_messages(text: str, template_id: str) -> list[dict[str, str]]:
    """
    Build the chat messages asking an auditor LLM for the emotion label and naturalness.

    Args:
        text: Diary entry to audit
        template_id: Template the entry was generated with; the auditor judges it against the
            same label descriptions the generator was given

    Returns:
        Chat messages (system + user)
    """
    descriptions = GENERATION_TEMPLATES[template_id][2]
    label_list = "\n".join(
        f"- {name}: {vi} ({description})" for name, (vi, description) in descriptions.items()
    )
    content = AUDIT_USER_TEMPLATE.format(text=text, label_list=label_list)
    return [
        {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def parse_audit_response(raw: str) -> tuple[str | None, bool | None]:
    """
    Parse the auditor's JSON answer.

    Args:
        raw: Raw auditor output

    Returns:
        (canonical label name or None, natural flag or None) — None where unparseable
    """
    match = _JSON_OBJECT.search(raw)
    if match is None:
        return None, None
    try:
        answer = json.loads(match.group())
    except json.JSONDecodeError:
        return None, None

    label = answer.get("label")
    idx = (
        find_label_index_by_name(DEFAULT_EMOTION_LABELS, label) if isinstance(label, str) else None
    )
    natural = answer.get("natural")
    return (
        DEFAULT_EMOTION_LABELS[idx] if idx is not None else None,
        natural if isinstance(natural, bool) else None,
    )
