# MoodNote AI - Vietnamese Emotion Classification

Repo đang được xây lại từ đầu để bám sát Nội dung 1 & 2 của đề cương NCKH 2026
("Nghiên cứu phân tích cảm xúc tiếng Việt và thuật toán gợi ý âm nhạc theo cảm
xúc, nhận biết ngữ cảnh"): sinh dữ liệu nhật ký giả lập bằng LLM mã nguồn mở
(Human-in-the-loop QA) + huấn luyện/đánh giá ablation mô hình PhoBERT trên
UIT-VSMEC.

Việc rebuild chia thành 7 phase tuần tự. **Phase 1-2 đã xong**: khung dự án,
`src/utils/*` carry-forward, schema validate config, CI lint; tải + tiền xử lý UIT-VSMEC.
**Phase 3**: code pipeline sinh dữ liệu + QA đã có, chờ chạy trên Colab và audit thủ công.

## Roadmap

1. ✅ Scaffold dự án + core utils (config, logger, emotion constants, metrics) + CI.
2. ✅ Dữ liệu thật (UIT-VSMEC): tải + tiền xử lý, giữ nguyên split train/validation/test gốc.
3. 🔧 Dữ liệu giả lập bằng LLM (Llama-3-8B-Instruct, Qwen3-8B) + Human-in-the-loop QA.
4. Huấn luyện PhoBERT + ablation 3 kịch bản (real-only/synthetic-only/combined).
5. Serving layer (inference/API), sửa công thức tính intensity.
6. Mở rộng testing & CI (models/training/inference thật).
7. Tài liệu cuối (methodology, kết quả) phục vụ báo cáo NCKH.

## Chuẩn bị dữ liệu thật (UIT-VSMEC)

```bash
.venv/Scripts/python.exe -m src.data.real.download_vsmec   # -> data/real/raw/{train,validation,test}.csv
.venv/Scripts/python.exe -m src.data.real.preprocess       # -> data/real/processed/{train,validation,test}.csv
```

`data/real/processed/test.csv` là tập kiểm thử cố định cho cả 3 kịch bản ablation: chỉ ghi
lần đầu, các lần chạy sau nếu kết quả khác sẽ báo lỗi thay vì ghi đè.

## Sinh dữ liệu giả lập + kiểm định (phase 3)

Sinh dữ liệu cần GPU: chạy `notebooks/datagen_colab.ipynb` trên Colab T4 (thử prompt → generate 2 model
→ filter → cross-LLM audit → xuất phiếu audit). Output lưu trên Drive, mọi bước tự resume.

```bash
python -m src.data.synthetic.generate --model llama        # -> data/synthetic/raw/llama.jsonl (Colab)
python -m src.data.synthetic.generate --model qwen         # -> data/synthetic/raw/qwen.jsonl  (Colab)
python -m src.data.synthetic.filter                        # -> data/synthetic/filtered/{pool,dropped}.jsonl
python -m src.qa.cross_llm_audit --auditor qwen            # Qwen chấm mẫu của Llama (Colab)
python -m src.qa.cross_llm_audit --auditor llama           # Llama chấm mẫu của Qwen (Colab)
python -m src.qa.manual_audit                              # -> data/synthetic/audit/{rater_a,rater_b}.csv
python -m src.qa.acceptance_gate                           # -> reports/qa_report_<template>.json + data/synthetic/accepted/
```

Audit thủ công: tác giả và cộng tác viên điền cột `label` của phiếu mình một cách độc lập (1 trong 7 nhãn
tiếng Anh), lưu dạng "CSV UTF-8", không sửa/xoá/đổi thứ tự dòng. Phiếu đánh số `stt`, không hiện id (id chứa
nhãn sinh); gate tự ghép lại theo mẫu seeded. Gate yêu cầu Cohen's Kappa và tỉ lệ cross-LLM đạt ngưỡng
`configs/qa_config.yaml`; không đạt thì không ghi `accepted/` — thêm template prompt mới trong
`src/data/synthetic/prompts.py`, đổi `prompt.instruction_template_id`, cất `data/synthetic/` của đợt cũ
sang chỗ khác rồi sinh lại từ đầu.

## Chạy lint

```bash
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
```

Cài môi trường: `pip install -r requirements.txt` (đầy đủ, gồm torch/transformers) hoặc
`pip install -r requirements-dev.txt` (chỉ ruff, giống CI).

Bộ test tạm gỡ theo yêu cầu chủ dự án — CI hiện chỉ lint.
