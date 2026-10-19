"""Lazy model loading helper shared by routes."""

import threading
from typing import Optional

from flask import current_app

from utils.prediction import ModelPredictor

_lock = threading.Lock()
_predictor: Optional[ModelPredictor] = None


def get_predictor() -> Optional[ModelPredictor]:
    global _predictor
    if _predictor is not None and _predictor.is_loaded():
        return _predictor
    with _lock:
        if _predictor is not None and _predictor.is_loaded():
            return _predictor
        try:
            p = ModelPredictor.get_instance(
                model_path=current_app.config.get("MODEL_PATH"),
                vectorizer_path=current_app.config.get("VECTORIZER_PATH"),
            )
            if not p.is_loaded():
                p.load_models()
            _predictor = p
            current_app.predictor = p
            current_app.logger.info("ML model loaded lazily")
            return _predictor
        except Exception as exc:
            current_app.logger.error(f"Lazy model load failed: {exc}")
            return None