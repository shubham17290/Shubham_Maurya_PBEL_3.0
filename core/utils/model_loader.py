"""Lazy model loading helper shared by routes."""

import threading

from flask import current_app

from core.config import BASE_DIR

_lock = threading.Lock()
_predictor = None


def get_predictor():
    global _predictor
    if _predictor is not None and _predictor.is_loaded():
        return _predictor
    with _lock:
        if _predictor is not None and _predictor.is_loaded():
            return _predictor
        try:
            backend = current_app.config.get("INFERENCE_BACKEND", "numpy").lower()
            if backend == "numpy":
                from core.utils.numpy_predictor import NumpyPredictor

                model_dir = BASE_DIR / "models" / "np_model"
                p = NumpyPredictor(str(model_dir))
            else:
                from core.utils.prediction import ModelPredictor

                p = ModelPredictor.get_instance(
                    model_path=current_app.config.get("MODEL_PATH"),
                    vectorizer_path=current_app.config.get("VECTORIZER_PATH"),
                )
            if not p.is_loaded():
                p.load_models()
            _predictor = p
            current_app.predictor = p
            current_app.logger.info("ML model loaded lazily (backend=%s)", backend)
            return _predictor
        except Exception as exc:
            current_app.logger.error(f"Lazy model load failed: {exc}")
            return None