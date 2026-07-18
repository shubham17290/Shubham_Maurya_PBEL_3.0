"""
Fake News Detection Application - Application Factory Pattern.
This module creates and configures the Flask application.
"""

import logging
import sys
from typing import Optional
from flask import Flask, render_template, flash

from config import get_config
from utils.prediction import ModelPredictor


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory function.
    Creates and configures the Flask application.
    """
    # Create Flask app instance
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = "development"

    config = get_config(config_name)
    app.config.from_object(config)

    # Initialize logging
    initialize_logging(app)

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


def initialize_components(app: Flask) -> None:
    try:
        app.logger.info("Initializing application components...")

        # Load ML model
        predictor = ModelPredictor.get_instance()
        predictor.load_models()

        # Store predictor in app context
        app.predictor = predictor

        # Initialize routes with predictor
        from routes.main import init_routes

        init_routes(predictor)

        # Initialize API routes with predictor
        from routes.api import init_api_routes

        init_api_routes(predictor)

        app.logger.info("✓ Application components initialized successfully")
        app.logger.info("✓ ML models loaded and ready")

    except FileNotFoundError as e:
        app.logger.critical(f"✗ Failed to initialize: Model files not found - {e}")
        app.logger.critical(
            "Please ensure model/model.pkl and model/vectorizer.pkl exist"
        )
        sys.exit(1)

    except Exception as e:
        app.logger.critical(f"✗ Failed to initialize application: {e}")
        app.logger.critical("Application cannot start without ML models")
        sys.exit(1)


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


# =========================================================================
# GUNICORN FIX: Expose 'app' at the global level so Render can find it
# =========================================================================
app = create_app("production")

# Application entry point for LOCAL testing
if __name__ == "__main__":
    app.logger.info("Starting Flask development server...")
    # Using .get() prevents KeyError if HOST or PORT aren't in config
    app.run(
        host=app.config.get("HOST", "0.0.0.0"),
        port=app.config.get("PORT", 5000),
        debug=app.config.get("DEBUG", True),
    )
