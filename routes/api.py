"""
API routes for Fake News Detection Application.
Provides REST API endpoints for programmatic access.
"""

from flask import Blueprint, request, jsonify, current_app, session
from typing import Dict
import logging
import math

from utils.prediction import ModelPredictor
from utils.rate_limit import limiter
from utils.model_loader import get_predictor
from utils.history import save_prediction, set_feedback, get_prediction, FEEDBACK_VALUES

# Create blueprint
api_bp = Blueprint('api', __name__)

# Global predictor instance
predictor: ModelPredictor = None

# Configure logger
logger = logging.getLogger(__name__)


def init_api_routes(predictor_instance: ModelPredictor) -> None:
    """
    Initialize API routes with predictor instance.

    Args:
        predictor_instance: Loaded ModelPredictor instance
    """
    global predictor
    predictor = predictor_instance


def _clean_probabilities(raw) -> Dict[str, float]:
    """Return a sanitized label -> probability mapping, or an empty dict.

    Values must be finite numbers within [0, 1]. Invalid or malformed output is
    dropped entirely rather than partially displayed (the client falls back to
    showing confidence only).
    """
    if not isinstance(raw, dict) or not raw:
        return {}
    cleaned = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            return {}
        try:
            fv = float(value)
        except (TypeError, ValueError):
            return {}
        if not math.isfinite(fv) or fv < 0.0 or fv > 1.0:
            return {}
        cleaned[key] = fv
    return cleaned


@api_bp.route('/predict', methods=['POST'])
@limiter.limit("20 per minute")
def api_predict():
    """
    API endpoint for prediction.

    Expects JSON payload with 'text' field containing news article.

    Request JSON:
        {
            "text": "News article text here..."
        }

    Returns:
        JSON response with prediction and confidence:
        {
            "success": true,
            "prediction": "Real News",
            "confidence": 0.95,
            "text_length": 1234
        }

    Error Response:
        {
            "success": false,
            "error": "Error message"
        }
    """
    try:
        # Lazily resolve predictor
        model = get_predictor()
        if model is None or not model.is_loaded():
            logger.error('API prediction attempted but model not loaded')
            return jsonify({
                'success': False,
                'error': 'Model not loaded. Please contact administrator.'
            }), 503

        # Get JSON data
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400

        # Get text from request
        text = data.get('text', '').strip()

        # Validate input using shared helper and configured thresholds
        from utils.validation import validate_news_text

        min_length = current_app.config.get("MIN_TEXT_LENGTH", 50)
        max_length = current_app.config.get("MAX_TEXT_LENGTH", 50000)
        validation_error = validate_news_text(text, min_length=min_length, max_length=max_length)
        if validation_error:
            return jsonify({
                'success': False,
                'error': validation_error
            }), 400

        # Make prediction
        try:
            result, confidence = model.predict(text)
        except ValueError as e:
            logger.warning(f'Invalid input for API prediction: {e}')
            return jsonify({
                'success': False,
                'error': f'Invalid input: {str(e)}'
            }), 400
        except RuntimeError as e:
            logger.error(f'API prediction runtime error: {e}')
            return jsonify({
                'success': False,
                'error': 'Prediction failed. Please try again.'
            }), 500

        # Per-class probabilities (best-effort, sanitized)
        probabilities = {}
        low_confidence = confidence < 0.6
        if hasattr(model, "predict_proba"):
            try:
                probabilities = _clean_probabilities(model.predict_proba(text))
            except Exception:
                probabilities = {}

        # Explainability (best-effort)
        explanation = None
        if hasattr(model, "explain"):
            try:
                explanation = model.explain(text, top_k=5)
            except Exception:
                explanation = None

        # Persist to history so the result can be reviewed and rated later.
        prediction_id = save_prediction(result, confidence, "single", text, "ok")

        # Log successful prediction
        logger.info(f'API prediction: {result} (confidence: {confidence:.2%})')

        # Return success response
        payload = {
            'success': True,
            'prediction': result,
            'confidence': confidence,
            'confidence_percentage': f'{confidence:.2%}',
            'low_confidence': low_confidence,
            'text_length': len(text)
        }
        if prediction_id is not None:
            payload['prediction_id'] = prediction_id
        if probabilities:
            payload['probabilities'] = probabilities
        if explanation is not None:
            payload['explanation'] = explanation
        return jsonify(payload), 200

    except Exception as e:
        logger.error(f'Unexpected error in API predict: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again later.'
        }), 500


@api_bp.route('/feedback', methods=['POST'])
@limiter.limit("30 per minute")
def api_feedback():
    """
    Record optional user feedback ("helpful" / "not_helpful") for a stored prediction.

    Request JSON:
        { "prediction_id": 12, "feedback": "helpful" }

    Policy: the first feedback submitted for a prediction is kept; later
    submissions are acknowledged but never overwrite it.
    """
    # CSRF validation for session-based state-changing requests
    if current_app.config.get("CSRF_ENABLED", True):
        token = request.headers.get("X-CSRF-Token") or (request.get_json(silent=True) or {}).get("csrf_token")
        if not token or token != session.get("csrf_token"):
            return jsonify({'success': False, 'error': 'Invalid or missing CSRF token.'}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

    try:
        pid = int(data.get('prediction_id'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'A valid prediction_id is required.'}), 400

    feedback = data.get('feedback')
    if feedback not in FEEDBACK_VALUES:
        return jsonify({'success': False, 'error': 'feedback must be "helpful" or "not_helpful".'}), 400

    status = set_feedback(pid, feedback)
    if status == 'set':
        return jsonify({'success': True, 'feedback': feedback}), 200
    if status == 'already_set':
        existing = get_prediction(pid) or {}
        return jsonify({
            'success': True,
            'already_recorded': True,
            'feedback': existing.get('feedback'),
            'message': 'Feedback was already recorded for this prediction.',
        }), 200
    if status == 'invalid':
        return jsonify({'success': False, 'error': 'feedback must be "helpful" or "not_helpful".'}), 400
    return jsonify({'success': False, 'error': 'Prediction not found.'}), 404


@api_bp.route('/health', methods=['GET'])
def api_health():
    """
    API health check endpoint.

    Returns:
        JSON response with health status
    """
    try:
        model = get_predictor()
        is_healthy = model is not None and model.is_loaded()

        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'model_loaded': is_healthy
        }), 200 if is_healthy else 503

    except Exception as e:
        logger.error(f'API health check failed: {e}')
        return jsonify({
            'status': 'unhealthy',
            'model_loaded': False,
            'error': str(e)
        }), 503


@api_bp.route('/info', methods=['GET'])
def api_info():
    """
    API information endpoint.

    Returns:
        JSON response with API information
    """
    return jsonify({
        'name': 'Fake News Detection API',
        'version': '1.0.0',
        'endpoints': {
            'POST /api/predict': 'Predict if news is real or fake',
            'POST /api/feedback': 'Record helpful / not_helpful feedback for a stored prediction',
            'GET /api/health': 'Health check endpoint',
            'GET /api/info': 'API information'
        },
        'model': 'Logistic Regression with TF-IDF',
        'usage': {
            'predict': 'POST JSON with {"text": "your news article here"}',
            'feedback': 'POST JSON with {"prediction_id": 1, "feedback": "helpful"}'
        }
    }), 200
