"""
Configuration management for Fake News Detection Application.
Supports different environments (development, production, testing).
"""

import os
from pathlib import Path

# Base directory of the project (used to resolve relative paths)
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration class with common settings."""

    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Request body limit (protects against oversized payloads). Kept slightly
    # above BATCH_MAX_FILE_SIZE to allow multipart/form-data overhead.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 6 * 1024 * 1024))

    # Model paths (resolved against BASE_DIR when relative)
    MODEL_PATH = os.environ.get("MODEL_PATH", "model/model.pkl")
    VECTORIZER_PATH = os.environ.get("VECTORIZER_PATH", "model/vectorizer.pkl")

    # Inference backend: "numpy" (no scikit-learn at runtime) or "sklearn"
    INFERENCE_BACKEND = os.environ.get("INFERENCE_BACKEND", "numpy").lower()

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Input validation
    MIN_TEXT_LENGTH = int(os.environ.get("MIN_TEXT_LENGTH", 50))
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", 50000))

    # Batch prediction limits
    BATCH_MAX_FILE_SIZE = int(os.environ.get("BATCH_MAX_FILE_SIZE", 5 * 1024 * 1024))
    BATCH_MAX_ROWS = int(os.environ.get("BATCH_MAX_ROWS", 1000))

    # Prediction history (SQLite)
    HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "history.db")
    HISTORY_EXCERPT_LENGTH = int(os.environ.get("HISTORY_EXCERPT_LENGTH", 300))

    # Server settings
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5000))

    # Session cookie hardening (safe defaults; production tightens further)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False

    # CSRF protection for form submissions
    CSRF_ENABLED = os.environ.get("CSRF_ENABLED", "true").lower() in ("1", "true", "yes")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True

    # Secret key MUST be provided via environment in production.
    SECRET_KEY = os.environ.get("SECRET_KEY")


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "test-secret-key")
    # Disable CSRF/secure cookies conveniences for tests
    SESSION_COOKIE_SECURE = False
    CSRF_ENABLED = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str = None) -> Config:
    """
    Get configuration based on environment.

    Args:
        env: Environment name (development, production, testing)

    Returns:
        Configuration object

    Raises:
        RuntimeError: If production is selected without a SECRET_KEY.
    """
    if env is None:
        env = os.environ.get("FLASK_ENV", "development")

    selected = config.get(env, config["default"])

    if env == "production" and not getattr(selected, "SECRET_KEY", None):
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production. "
            "Set it before starting the application."
        )

    return selected