"""scikit-learn-free inference using a NumPy/JSON model bundle."""

import json
import math
import re
from pathlib import Path
from typing import Tuple

import numpy as np

from utils.prediction import TextPreprocessor

LABEL_REAL = "Real News"
LABEL_FAKE = "Fake News"


class NumpyPredictor:
    """Drop-in replacement for ModelPredictor using only NumPy + stdlib."""

    def __init__(self, model_dir: str = "model/np_model"):
        self.model_dir = Path(model_dir)
        self.coef = None  # shape (1, n_features)
        self.intercept = None
        self.idf = None
        self.vocabulary = None  # token -> column index
        self.config = None
        self._token_re = None
        self._index_to_token = None

    def load_models(self) -> None:
        required = ["coef.npy", "intercept.npy", "idf.npy", "vocabulary.json", "config.json"]
        for name in required:
            if not (self.model_dir / name).exists():
                raise FileNotFoundError(f"Missing model file: {self.model_dir / name}")

        self.coef = np.load(self.model_dir / "coef.npy")
        self.intercept = np.load(self.model_dir / "intercept.npy")
        self.idf = np.load(self.model_dir / "idf.npy")

        vocab_raw = json.loads((self.model_dir / "vocabulary.json").read_text(encoding="utf-8"))
        self.vocabulary = {str(k): int(v) for k, v in vocab_raw.items()}

        self.config = json.loads((self.model_dir / "config.json").read_text(encoding="utf-8"))
        self._token_re = re.compile(self.config["token_pattern"])

        if self.coef.shape[1] != len(self.vocabulary):
            raise ValueError("Vocabulary size does not match coefficient count")

    def is_loaded(self) -> bool:
        return (
            self.coef is not None
            and self.intercept is not None
            and self.idf is not None
            and self.vocabulary is not None
        )

    def _tokenize(self, text: str):
        if self.config.get("lowercase", True):
            text = text.lower()
        # sklearn token_pattern finds all matches
        return self._token_re.findall(text)

    def _build_vector(self, text: str) -> np.ndarray:
        n_features = self.coef.shape[1]
        vec = np.zeros(n_features, dtype=np.float64)

        cleaned = TextPreprocessor.clean_text(text)
        tokens = self._tokenize(cleaned)

        ngram_min, ngram_max = self.config.get("ngram_range", [1, 1])
        # Generate n-grams
        grams = []
        for n in range(ngram_min, ngram_max + 1):
            for i in range(len(tokens) - n + 1):
                grams.append(" ".join(tokens[i : i + n]))

        # Term frequencies
        tf = {}
        for g in grams:
            idx = self.vocabulary.get(g)
            if idx is None:
                continue
            tf[idx] = tf.get(idx, 0) + 1

        if not tf:
            return vec

        # Apply idf + tf
        for idx, count in tf.items():
            tfidf = float(count)
            if self.config.get("sublinear_tf", False):
                tfidf = 1.0 + math.log(tfidf)
            if self.config.get("use_idf", True):
                tfidf *= float(self.idf[idx])
            vec[idx] = tfidf

        # L2 normalize
        norm = self.config.get("norm", "l2")
        if norm == "l2":
            n = np.linalg.norm(vec)
            if n > 0:
                vec = vec / n
        elif norm == "l1":
            n = np.abs(vec).sum()
            if n > 0:
                vec = vec / n

        return vec

    def predict(self, text: str) -> Tuple[str, float]:
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string")

        cleaned = TextPreprocessor.clean_text(text)
        if not cleaned.strip():
            raise ValueError("Input text contains no valid content after preprocessing")

        vec = self._build_vector(text)
        decision = float((self.coef @ vec).reshape(-1)[0]) + float(self.intercept.item())
        proba1 = 1.0 / (1.0 + math.exp(-decision))
        result = LABEL_REAL if proba1 >= 0.5 else LABEL_FAKE
        confidence = float(max(proba1, 1.0 - proba1))
        return result, confidence

    def predict_proba(self, text: str):
        cleaned = TextPreprocessor.clean_text(text)
        if not cleaned.strip():
            raise ValueError("Input text contains no valid content after preprocessing")
        vec = self._build_vector(text)
        decision = float((self.coef @ vec).reshape(-1)[0]) + float(self.intercept.item())
        proba1 = 1.0 / (1.0 + math.exp(-decision))
        return {"Fake News": float(1.0 - proba1), "Real News": float(proba1)}