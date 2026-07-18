"""
API routes for Fake News Detection Application.
Provides REST API endpoints for programmatic access.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Tuple
import logging

from utils.prediction import ModelPredictor

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


@api_bp.route('/predict', methods=['POST'])
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
        # Validate predictor is loaded
        if predictor is None or not predictor.is_loaded():
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

        # Validate input
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided. Please provide "text" field in JSON.'
            }), 400

        if len(text) < 50:
            return jsonify({
                'success': False,
                'error': 'Text too short. Minimum 50 characters required.'
            }), 400

        if len(text) > 50000:
            return jsonify({
                'success': False,
                'error': 'Text too long. Maximum 50,000 characters allowed.'
            }), 400

        # Make prediction
        try:
            result, confidence = predictor.predict(text)
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

        # Log successful prediction
        logger.info(f'API prediction: {result} (confidence: {confidence:.2%})')

        # Return success response
        return jsonify({
            'success': True,
            'prediction': result,
            'confidence': confidence,
            'confidence_percentage': f'{confidence:.2%}',
            'text_length': len(text)
        }), 200

    except Exception as e:
        logger.error(f'Unexpected error in API predict: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again later.'
        }), 500


@api_bp.route('/health', methods=['GET'])
def api_health():
    """
    API health check endpoint.

    Returns:
        JSON response with health status
    """
    try:
        is_healthy = predictor is not None and predictor.is_loaded()

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
            'GET /api/health': 'Health check endpoint',
            'GET /api/info': 'API information'
        },
        'model': 'Logistic Regression with TF-IDF',
        'usage': {
            'predict': 'POST JSON with {"text": "your news article here"}'
        }
    }), 200
