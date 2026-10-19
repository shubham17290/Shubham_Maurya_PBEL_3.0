"""
Main routes for Fake News Detection Application.
Handles web page routes.
"""

from flask import Blueprint, render_template, flash, request, current_app, session, redirect, url_for
import secrets
from typing import Optional

from utils.prediction import ModelPredictor
from utils.validation import validate_news_text
from utils.rate_limit import limiter
from utils.model_loader import get_predictor
from utils.batch import parse_csv_bytes, parse_txt_bytes, process_articles, results_to_csv
from utils.history import save_prediction, save_batch, list_predictions, count_predictions, get_prediction, clear_all

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
        save_prediction(result, confidence, "single", news_text, "ok")
        prediction_text = f'Prediction: {result} (Confidence: {confidence:.2%})'
        return render_template('index.html', prediction_text=prediction_text)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in predict: {e}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template('index.html')


def validate_input(text: str) -> Optional[str]:
    return validate_news_text(text)


@main_bp.route("/history", methods=["GET"])
def history_page():
    label = request.args.get("label")
    if label not in ("Real News", "Fake News", None, ""):
        label = None
    if label == "":
        label = None
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    if page > 10000:
        page = 10000
    per_page = 20
    offset = (page - 1) * per_page
    items = list_predictions(limit=per_page, offset=offset, label=label)
    total = count_predictions(label)
    pages = (total + per_page - 1) // per_page if total else 1
    csrf_token = None
    if current_app.config.get("CSRF_ENABLED", True):
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token
    return render_template(
        "history.html",
        items=items,
        page=page,
        pages=pages,
        total=total,
        label=label or "",
        csrf_token=csrf_token,
    )


@main_bp.route("/history/<int:pid>", methods=["GET"])
def history_detail(pid):
    item = get_prediction(pid)
    if not item:
        flash("Prediction not found.", "warning")
        return render_template("history.html", items=[], page=1, pages=1, total=0, label="")
    return render_template("history_detail.html", item=item)


@main_bp.route("/history/clear", methods=["POST"])
def history_clear():
    if current_app.config.get("CSRF_ENABLED", True):
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            flash("Invalid or missing CSRF token.", "danger")
            return render_template("history.html", items=[], page=1, pages=1, total=0, label="")
    ok = clear_all()
    if ok:
        flash("History cleared.", "success")
    else:
        flash("Could not clear history.", "danger")
    return redirect(url_for("main.history_page"))


@main_bp.route("/batch", methods=["GET"])
def batch_form():
    csrf_token = None
    if current_app.config.get("CSRF_ENABLED", True):
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token
    return render_template("batch.html", csrf_token=csrf_token)


@main_bp.route("/batch", methods=["POST"])
def batch_process():
    if current_app.config.get("CSRF_ENABLED", True):
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            flash("Invalid or missing CSRF token. Please refresh and try again.", "danger")
            return render_template("batch.html"), 400

    if "file" not in request.files:
        flash("No file uploaded.", "danger")
        return render_template("batch.html")

    f = request.files["file"]
    if not f or not f.filename:
        flash("No file selected.", "danger")
        return render_template("batch.html")

    filename = f.filename.lower()
    if not (filename.endswith(".csv") or filename.endswith(".txt")):
        flash("Unsupported file type. Please upload a CSV or TXT file.", "danger")
        return render_template("batch.html")

    data = f.read()
    max_size = current_app.config.get("BATCH_MAX_FILE_SIZE", 5 * 1024 * 1024)
    if len(data) == 0:
        flash("Uploaded file is empty.", "danger")
        return render_template("batch.html")
    if len(data) > max_size:
        flash(f"File too large. Maximum {max_size // (1024*1024)} MB allowed.", "danger")
        return render_template("batch.html")

    try:
        if filename.endswith(".csv"):
            articles = parse_csv_bytes(data)
        else:
            articles = parse_txt_bytes(data)
    except Exception as exc:
        current_app.logger.warning("Batch file parse failed: %s", exc)
        flash("Could not parse file. Please check the format and try again.", "danger")
        return render_template("batch.html")

    max_rows = current_app.config.get("BATCH_MAX_ROWS", 1000)
    if len(articles) == 0:
        flash("No articles found in file.", "danger")
        return render_template("batch.html")
    if len(articles) > max_rows:
        flash(f"Too many rows. Maximum {max_rows} articles allowed.", "danger")
        return render_template("batch.html")

    model = get_predictor()
    if model is None or not model.is_loaded():
        flash("Model not loaded. Please try again later.", "danger")
        return render_template("batch.html")

    results = process_articles(
        articles,
        model,
        min_length=current_app.config.get("MIN_TEXT_LENGTH", 50),
        max_length=current_app.config.get("MAX_TEXT_LENGTH", 50000),
    )

    csv_bytes = results_to_csv(results)
    import base64
    session["batch_csv"] = base64.b64encode(csv_bytes).decode("ascii")
    session["batch_filename"] = "predictions.csv"

    save_batch(results, "batch")

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = len(results) - ok
    preview = results[:20]

    return render_template(
        "batch_results.html",
        total=len(results),
        successful=ok,
        failed=failed,
        preview=preview,
    )


@main_bp.route("/batch/download", methods=["GET"])
def batch_download():
    import base64
    b64 = session.get("batch_csv")
    if not b64:
        flash("No batch results available. Please upload a file first.", "warning")
        return render_template("batch.html")
    data = base64.b64decode(b64)
    from flask import Response
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=predictions.csv"},
    )