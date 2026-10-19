"""
Prediction utilities for Fake News Detection.
Contains text preprocessing and model prediction functions.
"""

import re
import math
import pickle
import logging
from typing import Tuple, Optional
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Text preprocessing class for cleaning news articles."""

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and preprocess text data.

        Args:
            text: Raw text input

        Returns:
            Cleaned text string
        """
        # Convert to string and lowercase
        text = str(text).lower()

        # Remove URLs
        text = re.sub(r"https?://\S+|www\.\S+", "", text)

        # Remove HTML tags
        text = re.sub(r"<.*?>", "", text)

        # Remove punctuation
        text = re.sub(r"[^\w\s]", "", text)

        # Remove digits
        text = re.sub(r"\d", "", text)

        # Remove newline characters
        text = re.sub(r"\n", " ", text)

        return text


class ModelPredictor:
    """
    Model predictor class for loading models and making predictions.

    This class follows the singleton pattern to ensure models are loaded only once.
    """

    _instance: Optional['ModelPredictor'] = None

    def __init__(self, model_path: str = "model/model.pkl",
                 vectorizer_path: str = "model/vectorizer.pkl"):
        """
        Initialize the predictor with model and vectorizer paths.

        Args:
            model_path: Path to the trained model pickle file
            vectorizer_path: Path to the vectorizer pickle file
        """
        self.model_path = Path(model_path)
        self.vectorizer_path = Path(vectorizer_path)
        self.model = None
        self.vectorizer = None
        self.preprocessor = TextPreprocessor()

    @classmethod
    def get_instance(cls, model_path: Optional[str] = None,
                     vectorizer_path: Optional[str] = None) -> 'ModelPredictor':
        """
        Get (or create) the singleton instance of ModelPredictor.

        Paths can be supplied on the first call; later calls keep the
        existing paths unless the models have not been loaded yet.
        """
        if cls._instance is None:
            cls._instance = cls(
                model_path or "model/model.pkl",
                vectorizer_path or "model/vectorizer.pkl",
            )
        else:
            if model_path is not None and cls._instance.model is None:
                cls._instance.model_path = Path(model_path)
            if vectorizer_path is not None and cls._instance.vectorizer is None:
                cls._instance.vectorizer_path = Path(vectorizer_path)
        return cls._instance

    def load_models(self) -> None:
        """
        Load the trained model and vectorizer from pickle files.

        Raises:
            FileNotFoundError: If model or vectorizer files are not found
            ValueError: If model files are corrupted or invalid
            Exception: If there's an error loading the models
        """
        try:
            # Validate model files exist
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model file not found at: {self.model_path.absolute()}"
                )

            if not self.vectorizer_path.exists():
                raise FileNotFoundError(
                    f"Vectorizer file not found at: {self.vectorizer_path.absolute()}"
                )

            # Load model
            logger.info(f"Loading model from {self.model_path}")
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)

            # Load vectorizer
            logger.info(f"Loading vectorizer from {self.vectorizer_path}")
            with open(self.vectorizer_path, "rb") as f:
                self.vectorizer = pickle.load(f)

            # Validate loaded objects
            if self.model is None:
                raise ValueError("Model loaded as None")

            if self.vectorizer is None:
                raise ValueError("Vectorizer loaded as None")

            logger.info("Models loaded successfully")

        except FileNotFoundError as e:
            logger.error(f"Model file not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid model file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise Exception(f"Failed to load ML models: {str(e)}") from e

    def is_loaded(self) -> bool:
        """
        Check if models are loaded.

        Returns:
            True if both model and vectorizer are loaded, False otherwise
        """
        return self.model is not None and self.vectorizer is not None

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Make a prediction on the given text.

        Args:
            text: Raw news article text

        Returns:
            Tuple of (prediction_label, confidence_score)

        Raises:
            RuntimeError: If models are not loaded
            ValueError: If input text is invalid
        """
        # Validate models are loaded
        if not self.is_loaded():
            raise RuntimeError(
                "Models not loaded. Call load_models() before making predictions."
            )

        # Validate input
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string")

        # Clean the text
        cleaned_text = self.preprocessor.clean_text(text)

        # Check if cleaned text is empty
        if not cleaned_text or len(cleaned_text.strip()) == 0:
            raise ValueError(
                "Input text contains no valid content after preprocessing"
            )

        try:
            # Vectorize the text
            vectorized_text = self.vectorizer.transform([cleaned_text])

            # Make prediction
            prediction = self.model.predict(vectorized_text)

            # Get confidence score if available
            confidence = 1.0
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(vectorized_text)
                confidence = float(proba.max())

            # Convert prediction to label
            result = "Real News" if prediction[0] == 1 else "Fake News"

            logger.debug(f"Prediction: {result} with confidence {confidence:.4f}")

            return result, confidence

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            raise RuntimeError(f"Prediction failed: {str(e)}") from e

    def predict_proba(self, text: str):
        """Return per-class probabilities for the given text."""
        if not self.is_loaded():
            raise RuntimeError("Models not loaded. Call load_models() before making predictions.")
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string")

        cleaned_text = self.preprocessor.clean_text(text)
        if not cleaned_text or len(cleaned_text.strip()) == 0:
            raise ValueError("Input text contains no valid content after preprocessing")

        vectorized_text = self.vectorizer.transform([cleaned_text])
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(vectorized_text)[0]
            classes = list(self.model.classes_)
        else:
            # Fallback: synthesize from decision function
            decision = float(self.model.decision_function(vectorized_text)[0])
            p1 = 1.0 / (1.0 + math.exp(-decision))
            proba = [1 - p1, p1]
            classes = [0, 1]

        mapping = {}
        for cls, p in zip(classes, proba):
            label = "Real News" if cls == 1 else "Fake News"
            mapping[label] = float(p)
        return mapping

    def explain(self, text: str, top_k: int = 5):
        if not self.is_loaded():
            raise RuntimeError("Models not loaded. Call load_models() before making predictions.")
        cleaned_text = self.preprocessor.clean_text(text)
        if not cleaned_text or len(cleaned_text.strip()) == 0:
            raise ValueError("Input text contains no valid content after preprocessing")

        vectorized = self.vectorizer.transform([cleaned_text])
        # dense contributions
        vec = vectorized.toarray().reshape(-1)
        coef = self.model.coef_.reshape(-1)
        contrib = coef * vec

        # map feature index -> name
        feature_names = self.vectorizer.get_feature_names_out()
        features = []
        for idx, c in enumerate(contrib):
            if c == 0:
                continue
            features.append({"feature": str(feature_names[idx]), "contribution": float(c)})

        supporting = sorted([f for f in features if f["contribution"] > 0], key=lambda x: x["contribution"], reverse=True)[:top_k]
        opposing = sorted([f for f in features if f["contribution"] < 0], key=lambda x: x["contribution"])[:top_k]

        return {
            "supporting": supporting,
            "opposing": opposing,
            "note": "Contributions are (TF-IDF value x model weight). Positive supports 'Real News'; negative supports 'Fake News'. Approximate linear explanation.",
        }


