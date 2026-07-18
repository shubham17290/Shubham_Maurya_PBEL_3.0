"""
Main routes for Fake News Detection Application.
Handles web page routes.
"""

from flask import Blueprint, render_template, flash, request
from typing import Optional

from utils.prediction import ModelPredictor

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


@main_bp.route('/predict', methods=['POST'])
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

        # Validate input
        validation_error = validate_input(news_text)
        if validation_error:
            flash(validation_error, 'warning')
            return render_template('index.html')

        # Log prediction request
        from flask import current_app
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
        from flask import current_app
        current_app.logger.error(f'Unexpected error in predict: {e}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template('index.html')


def validate_input(text: str) -> Optional[str]:
    """
    Validate user input for prediction.

    Args:
        text: User input text

    Returns:
        Error message if validation fails, None if valid
    """
    if not text or not isinstance(text, str):
        return 'Please enter some news text to analyze.'

    text = text.strip()

    if len(text) == 0:
        return 'Please enter some news text to analyze.'

    if len(text) < 50:
        return 'Please enter a longer text (at least 50 characters) for accurate prediction.'

    if len(text) > 50000:
        return 'Text is too long. Please enter less than 50,000 characters.'

    # Check if text contains only whitespace or special characters
    if not any(char.isalnum() for char in text):
        return 'Please enter valid text with alphanumeric characters.'

    return None
