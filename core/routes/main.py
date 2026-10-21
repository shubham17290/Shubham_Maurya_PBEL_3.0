"""
Main routes for Fake News Detection Application.
Handles web page routes.
"""

from flask import Blueprint, render_template, flash, request, current_app, session
import secrets
from typing import Optional

from core.utils.prediction import ModelPredictor
from core.utils.validation import validate_news_text
from core.utils.rate_limit import limiter
from core.utils.model_loader import get_predictor

# Create blueprint
main_bp = Blueprint('main', __name__)

# Global predictor instance (resolved lazily)
predictor: Optional[ModelPredictor] = None


def init_routes(predictor_instance: Optional[ModelPredictor]) -> None:
    global predictor
    predictor = predictor_instance


@main_bp.route('/')
def home():
    csrf_token = None
    if current_app.config.get("CSRF_ENABLED", True):
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token
    return render_template('index.html', csrf_token=csrf_token)


@main_bp.route('/health', methods=['GET'])
def health():
    from flask import jsonify
    p = get_predictor()
    is_healthy = p is not None and p.is_loaded()
    return jsonify({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'model_loaded': is_healthy
    }), (200 if is_healthy else 503)


@main_bp.route('/predict', methods=['POST'])
@limiter.limit("10 per minute")
def predict():
    try:
        # CSRF validation for form submissions
        if current_app.config.get("CSRF_ENABLED", True):
            token = request.form.get("csrf_token")
            if not token or token != session.get("csrf_token"):
                flash("Invalid or missing CSRF token. Please refresh and try again.", "danger")
                return render_template('index.html'), 400

        model = get_predictor()
        if model is None or not model.is_loaded():
            flash('System error: Model not loaded. Please contact administrator.', 'danger')
            return render_template('index.html')

        news_text = request.form.get('news_input', '').strip()

        validation_error = validate_news_text(
            news_text,
            min_length=current_app.config.get("MIN_TEXT_LENGTH", 50),
            max_length=current_app.config.get("MAX_TEXT_LENGTH", 50000),
        )
        if validation_error:
            flash(validation_error, 'warning')
            return render_template('index.html')

        current_app.logger.info(f'Processing prediction request ({len(news_text)} chars)')

        try:
            result, confidence = model.predict(news_text)
        except ValueError as e:
            current_app.logger.warning(f'Invalid input: {e}')
            flash(f'Invalid input: {str(e)}', 'warning')
            return render_template('index.html')
        except RuntimeError as e:
            current_app.logger.error(f'Prediction error: {e}')
            flash('Prediction failed. Please try again.', 'danger')
            return render_template('index.html')

        current_app.logger.info(f'Prediction: {result} (confidence: {confidence:.2%})')
        prediction_text = f'Prediction: {result} (Confidence: {confidence:.2%})'
        return render_template('index.html', prediction_text=prediction_text)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in predict: {e}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template('index.html')


def validate_input(text: str) -> Optional[str]:
    return validate_news_text(text)