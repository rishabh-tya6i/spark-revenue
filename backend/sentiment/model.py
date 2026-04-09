import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)

class SentimentModel:
    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.model_name = model_name
        self.pipeline = None
        self.stub_mode = os.getenv("SENTIMENT_STUB_MODE", "false").lower() == "true"

    def _lazy_init(self):
        if self.pipeline is None and not self.stub_mode:
            from transformers import pipeline
            logger.info(f"Loading sentiment model: {self.model_name}")
            self.pipeline = pipeline("sentiment-analysis", model=self.model_name)

    def predict(self, texts: List[str]) -> List[Tuple[float, str]]:
        """
        Returns a list of (score, label) for each text.
        score is signed: Positive -> 1.0, Negative -> -1.0, Neutral -> 0.0 (weighted by confidence).
        """
        if not texts:
            return []

        if self.stub_mode:
            # Simple stub matching some keywords for basic testing
            results = []
            for text in texts:
                text_l = text.lower()
                if any(word in text_l for word in ["bull", "up", "rise", "gain", "high"]):
                    results.append((0.8, "positive"))
                elif any(word in text_l for word in ["bear", "down", "fall", "loss", "low"]):
                    results.append((-0.8, "negative"))
                else:
                    results.append((0.0, "neutral"))
            return results

        self._lazy_init()
        
        # transformers pipeline returns list of dicts: [{'label': 'positive', 'score': 0.99}, ...]
        raw_results = self.pipeline(texts)
        
        processed_results = []
        for res in raw_results:
            label = res['label'].lower()
            conf = res['score']
            
            # Map to signed score
            if label == "positive":
                score = conf
            elif label == "negative":
                score = -conf
            else:
                score = 0.0
                
            processed_results.append((score, label))
            
        return processed_results
