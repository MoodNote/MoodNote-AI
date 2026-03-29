"""
Prediction utilities for emotion classification
"""
import torch
import numpy as np
from pathlib import Path
from ..models.model_utils import load_model
from ..data.preprocess import VietnamesePreprocessor
from ..utils.keyword_extractor import VietnameseKeywordExtractor
from ..utils.logger import get_logger
from ..utils.emotion_constants import (
    normalize_emotion_labels,
    normalize_sentiment_scores,
    find_label_index_by_name,
)


logger = get_logger("predictor")


class EmotionPredictor:
    """Emotion predictor with Vietnamese preprocessing"""

    def __init__(
        self,
        model_path,
        device='cpu',
        segmenter='pyvi',
        emotion_labels=None,
        sentiment_scores=None
    ):
        """
        Initialize predictor

        Args:
            model_path: Path to saved model
            device: Device to run inference on
            segmenter: Vietnamese word segmenter to use
            emotion_labels: Dictionary mapping label indices to names
            sentiment_scores: Dictionary mapping emotion names to sentiment values (-1 to +1)
        """
        self.device = device
        self.model_path = model_path

        self.emotion_labels = normalize_emotion_labels(emotion_labels)
        self.other_label_index = find_label_index_by_name(self.emotion_labels, "Other")
        if self.other_label_index is None:
            logger.warning('No "Other" label found in emotion_labels; low-confidence fallback is disabled.')

        self.sentiment_scores = normalize_sentiment_scores(sentiment_scores)

        # Load model and tokenizer
        logger.info(f"Loading model from {model_path}...")
        self.model, self.tokenizer = load_model(model_path, device=device)

        # Initialize preprocessor
        self.preprocessor = VietnamesePreprocessor(segmenter=segmenter)

        # Initialize keyword extractor (FR-13)
        self.keyword_extractor = VietnameseKeywordExtractor(max_keywords=10)

        logger.info("Predictor initialized successfully!")

    def preprocess_text(self, text):
        """
        Preprocess Vietnamese text

        Args:
            text: Input text

        Returns:
            str: Preprocessed text
        """
        return self.preprocessor.segment_text(text)

    def predict(self, text, return_probabilities=True, other_threshold=0.0):
        """
        Predict emotion for a single text

        Args:
            text: Input Vietnamese text
            return_probabilities: Whether to return probabilities for all classes
            other_threshold: If max(softmax) < threshold, predict "Other" instead.
                             Set > 0 to catch low-confidence predictions as "Other"
                             (e.g. 0.40 works well for this model).
                             Default 0.0 = disabled (original argmax behavior).

        Returns:
            dict: Prediction results
        """
        # Preprocess text
        processed_text = self.preprocess_text(text)

        # Tokenize
        inputs = self.tokenizer(
            processed_text,
            max_length=128,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Inference
        with torch.no_grad():
            outputs = self.model(
                input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask']
            )

        # Get probabilities
        logits = outputs.logits if hasattr(outputs, 'logits') else outputs
        probs = torch.softmax(logits, dim=-1)
        probs = probs.cpu().numpy()[0]

        # Get prediction
        max_prob = float(np.max(probs))
        if (
            other_threshold > 0
            and max_prob < other_threshold
            and self.other_label_index is not None
        ):
            pred_idx = self.other_label_index
        else:
            pred_idx = int(np.argmax(probs))
        pred_emotion = self.emotion_labels.get(pred_idx, str(pred_idx))
        confidence = float(probs[pred_idx])

        # FR-11: Sentiment score (-1.0 to +1.0) — weighted sum of emotion sentiments
        sentiment_score = float(sum(
            self.sentiment_scores.get(self.emotion_labels.get(i, ""), 0.0) * float(prob)
            for i, prob in enumerate(probs)
        ))
        sentiment_score = round(sentiment_score, 4)

        # FR-12: Intensity (0-100) — based on prediction entropy
        # Low entropy = model is confident = high intensity
        entropy = -np.sum(probs * np.log(probs + 1e-9))
        max_entropy = np.log(len(probs))  # log(7) ≈ 1.946
        intensity = round(float((1.0 - entropy / max_entropy) * 100), 2)

        # FR-13: Keyword extraction (3-10 keywords)
        keywords = self.keyword_extractor.extract(text, n=5)

        # Create result
        result = {
            'text': text,
            'emotion': pred_emotion,
            'confidence': confidence,
            'sentiment_score': sentiment_score,
            'intensity': intensity,
            'keywords': keywords
        }

        if return_probabilities:
            result['probabilities'] = {
                self.emotion_labels.get(i, str(i)): float(prob)
                for i, prob in enumerate(probs)
            }

        return result

    def predict_batch(self, texts, return_probabilities=True):
        """
        Predict emotions for a batch of texts

        Args:
            texts: List of Vietnamese texts
            return_probabilities: Whether to return probabilities

        Returns:
            list: List of prediction results
        """
        results = []

        for text in texts:
            result = self.predict(text, return_probabilities=return_probabilities)
            results.append(result)

        return results


if __name__ == "__main__":
    # Test predictor
    print("Testing emotion predictor...")

    # Note: This requires a trained model
    model_path = "models/best_model"

    if Path(model_path).exists():
        predictor = EmotionPredictor(
            model_path=model_path,
            device='cpu'
        )

        # Test texts
        test_texts = [
            "Hôm nay tôi rất vui và hạnh phúc",
            "Tôi cảm thấy buồn và mệt mỏi",
            "Tôi rất tức giận về điều này"
        ]

        print("\nPredictions:")
        for text in test_texts:
            result = predictor.predict(text)
            print(f"\nText: {text}")
            print(f"Emotion: {result['emotion']}")
            print(f"Confidence: {result['confidence']:.4f}")
            print(f"Probabilities: {result['probabilities']}")
    else:
        print(f"Model not found at {model_path}")
        print("Please train the model first using scripts/train.py")
