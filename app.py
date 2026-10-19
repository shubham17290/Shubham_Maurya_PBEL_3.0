"""
Fake News Detection Application - Application Factory Pattern.
This module creates and configures the Flask application.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, flash

from config import BASE_DIR, get_config
from utils.prediction import ModelPredictor
from utils.rate_limit import limiter


def _resolve_path(value: str) -> Path:
    """Resolve a (possibly relative) path against the project base directory."""
    path = Path(value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory function.
    Creates and configures the Flask application.
    """
    # Create Flask app instance
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config = get_config(config_name)
    app.config.from_object(config)

    # Resolve model paths against the project root
    app.config["MODEL_PATH"] = str(_resolve_path(app.config["MODEL_PATH"]))
    app.config["VECTORIZER_PATH"] = str(_resolve_path(app.config["VECTORIZER_PATH"]))

    # Initialize logging
    initialize_logging(app)

    # Initialize security extensions (headers + rate limiting)
    initialize_security(app)

    # Initialize extensions and components
    initialize_components(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    return app


def initialize_logging(app: Flask) -> None:
    if not app.debug and not app.testing:
        # Production logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
    else:
        # Development logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    app.logger.info("Logging initialized")


def initialize_security(app: Flask) -> None:
    """Configure security headers and rate limiting."""
    try:
        from flask_talisman import Talisman

        Talisman(
            app,
            force_https=not (app.debug or app.testing),
            strict_transport_security=not (app.debug or app.testing),
            content_security_policy={
                "default-src": "'self'",
                "style-src": ["'self'", "'unsafe-inline'"],
                "img-src": ["'self'", "data:"],
            },
        )
    except Exception as exc:  # pragma: no cover - defensive
        app.logger.warning(f"Talisman not enabled: {exc}")

    limiter.init_app(app)
    app.logger.info("Security extensions initialized")


def initialize_components(app: Flask) -> None:
    app.logger.info("Initializing application components...")

    # Model is loaded lazily on first request to keep cold starts fast and
    # allow the app to boot even if the model files are temporarily missing.
    predictor = None
    app.predictor = predictor

    # Initialize routes (predictor will be resolved lazily)
    from routes.main import init_routes

    init_routes(predictor)

    # Initialize API routes (predictor will be resolved lazily)
    from routes.api import init_api_routes

    init_api_routes(predictor)

    app.logger.info("Application components initialized (model will load lazily)")


def register_blueprints(app: Flask) -> None:
    from routes import main_bp, api_bp

    # Register main blueprint
    app.register_blueprint(main_bp)

    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix="/api")

    app.logger.info("Blueprints registered")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f"404 error: {error}")
        return render_template("index.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 error: {error}", exc_info=True)
        flash("An internal server error occurred. Please try again later.", "danger")
        return render_template("index.html"), 500

    @app.errorhandler(405)
    def method_not_allowed(error):
        app.logger.warning(f"405 error: {error}")
        flash("Method not allowed.", "warning")
        return render_template("index.html"), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        app.logger.warning(f"413 error: {error}")
        flash("Request payload too large.", "warning")
        return render_template("index.html"), 413

    app.logger.info("Error handlers registered")


# Expose 'app' at module level so WSGI servers (gunicorn, vercel) can find it.
# Default to development unless FLASK_ENV says otherwise.
app = create_app()

# Application entry point for LOCAL testing
if __name__ == "__main__":
    app.logger.info("Starting Flask development server...")
    app.run(
        host=app.config.get("HOST", "0.0.0.0"),
        port=app.config.get("PORT", 5000),
        debug=app.config.get("DEBUG", False),
    )