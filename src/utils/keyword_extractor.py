"""
Vietnamese keyword extraction using YAKE algorithm
"""


class VietnameseKeywordExtractor:
    """
    Keyword extractor for Vietnamese text using YAKE (Yet Another Keyword Extractor).

    YAKE is an unsupervised, language-independent keyword extractor that works
    well with Vietnamese text pre-segmented by pyvi (words joined by underscores).
    Lower YAKE score = more important keyword.
    """

    def __init__(self, max_keywords=10):
        """
        Initialize YAKE keyword extractor.

        Args:
            max_keywords: Maximum number of keywords to extract (upper bound)
        """
        try:
            import yake
        except ImportError:
            raise ImportError(
                "YAKE is required for keyword extraction. "
                "Install it with: pip install yake"
            )

        self.max_keywords = max_keywords
        self.extractor = yake.KeywordExtractor(
            lan="vi",
            n=1,            # unigrams only
            dedupLim=0.7,   # deduplication threshold
            top=max_keywords,
            features=None
        )

    def extract(self, text, n=5):
        """
        Extract keywords from Vietnamese text.

        Args:
            text: Vietnamese text (pyvi-segmented text works best)
            n: Number of keywords to return (clamped to 3-10)

        Returns:
            List[str]: Extracted keywords sorted by importance
        """
        n = max(3, min(n, self.max_keywords))

        if not text or not text.strip():
            return []

        keywords = self.extractor.extract_keywords(text)

        # YAKE returns (keyword, score) — lower score = more important
        result = [kw[0].replace("_", " ") for kw in keywords[:n]]

        return result


if __name__ == "__main__":
    extractor = VietnameseKeywordExtractor()

    test_texts = [
        "Hôm nay tôi rất buồn và mệt mỏi vì bị mất việc làm, không biết làm gì tiếp theo",
        "Tôi cảm thấy vui và hạnh phúc khi được gặp lại bạn bè sau bao lâu",
        "Tôi tức giận vì bị đối xử không công bằng tại nơi làm việc"
    ]

    for text in test_texts:
        keywords = extractor.extract(text, n=5)
        print(f"Text: {text[:50]}...")
        print(f"Keywords: {keywords}\n")
