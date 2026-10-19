"""
Main routes for Fake News Detection Application.
Handles web page routes.
"""

from flask import Blueprint, render_template, flash, request, current_app
from typing import Optional

from utils.prediction import ModelPredictor
from utils.validation import validate_news_text
from utils.rate_limit import limiter

# Create blueprint
main_bp = Blueprint('main', __name__)

# Global predictor instance (will be set during app initialization)
predictor: Optional[ModelPredictor] = None


def init_routes(predictor_instance: ModelPredictor) -> None:
    """
    Initialize routes with predictor instance.

    Args:
        predictor_instance: Loaded ModelPredictor instance
    """
    global predictor
    predictor = predictor_instance


@main_bp.route('/')
def home():
    """
    Render the home page with prediction form.

    Returns:
        Rendered index.html template
    """
    return render_template('index.html')


@main_bp.route('/health', methods=['GET'])
def health():
    """Convenience health check (alias of /api/health)."""
    from flask import jsonify
    is_healthy = predictor is not None and predictor.is_loaded()
    return jsonify({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'model_loaded': is_healthy
    }), (200 if is_healthy else 503)


@main_bp.route('/predict', methods=['POST'])
@limiter.limit("10 per minute")
def predict():
    """
    Handle prediction requests from the form.

    Validates input, makes prediction using ML model,
    and returns results with confidence score.

    Returns:
        Rendered template with prediction results or error messages
    """
    try:
        # Validate predictor is loaded
        if predictor is None or not predictor.is_loaded():
            flash('System error: Model not loaded. Please contact administrator.', 'danger')
            return render_template('index.html')

        # Get input from form
        news_text = request.form.get('news_input', '').strip()

        # Validate input using shared helper and configured thresholds
        validation_error = validate_news_text(
            news_text,
            min_length=current_app.config.get("MIN_TEXT_LENGTH", 50),
            max_length=current_app.config.get("MAX_TEXT_LENGTH", 50000),
        )
        if validation_error:
            flash(validation_error, 'warning')
            return render_template('index.html')

        # Log prediction request
        current_app.logger.info(f'Processing prediction request ({len(news_text)} chars)')

        # Make prediction
        try:
            result, confidence = predictor.predict(news_text)
        except ValueError as e:
            current_app.logger.warning(f'Invalid input: {e}')
            flash(f'Invalid input: {str(e)}', 'warning')
            return render_template('index.html')
        except RuntimeError as e:
            current_app.logger.error(f'Prediction error: {e}')
            flash('Prediction failed. Please try again.', 'danger')
            return render_template('index.html')

        # Log successful prediction
        current_app.logger.info(f'Prediction: {result} (confidence: {confidence:.2%})')

        # Format result
        prediction_text = f'Prediction: {result} (Confidence: {confidence:.2%})'

        return render_template('index.html', prediction_text=prediction_text)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in predict: {e}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template('index.html')


# Backwards-compatible alias for older callers/tests
def validate_input(text: str) -> Optional[str]:
    return validate_news_text(text)
