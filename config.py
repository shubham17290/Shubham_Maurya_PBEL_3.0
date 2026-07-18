"""
Configuration management for Fake News Detection Application.
Supports different environments (development, production, testing).
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent


class Config:
    """Base configuration class with common settings."""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False

    # Model paths
    MODEL_PATH = os.environ.get('MODEL_PATH', 'model/model.pkl')
    VECTORIZER_PATH = os.environ.get('VECTORIZER_PATH', 'model/vectorizer.pkl')

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Input validation
    MIN_TEXT_LENGTH = 50
    MAX_TEXT_LENGTH = 50000

    # Server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production

    # Use environment variables for sensitive data
    MODEL_PATH = os.environ.get('MODEL_PATH', 'model/model.pkl')
    VECTORIZER_PATH = os.environ.get('VECTORIZER_PATH', 'model/vectorizer.pkl')


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """
    Get configuration based on environment.

    Args:
        env: Environment name (development, production, testing)

    Returns:
        Configuration object
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
