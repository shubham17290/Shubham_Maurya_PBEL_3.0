"""
Main routes for Fake News Detection Application.
Handles web page routes.
"""

from flask import Blueprint, render_template, flash, request, current_app, session, redirect, url_for
import secrets
from typing import Optional

from core.utils.prediction import ModelPredictor
from core.utils.validation import validate_news_text
from core.utils.rate_limit import limiter
from core.utils.model_loader import get_predictor
from core.utils.batch import parse_csv_bytes, parse_txt_bytes, process_articles, results_to_csv
from core.utils.history import save_prediction, save_batch, list_predictions, count_predictions, get_prediction, clear_all

# Create blueprint
main_bp = Blueprint('main', __name__)

# Global predictor instance (resolved lazily)
predictor: Optional[ModelPredictor] = None


def init_routes(predictor_instance: Optional[ModelPredictor]) -> None:
    global predictor
    predictor = predictor_instance


def _get_csrf_token() -> Optional[str]:
    """Return the session CSRF token, creating it when protection is enabled."""
    if not current_app.config.get("CSRF_ENABLED", True):
        return None
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _csrf_valid() -> bool:
    """Validate the CSRF token on a form submission when protection is enabled."""
    if not current_app.config.get("CSRF_ENABLED", True):
        return True
    token = request.form.get("csrf_token")
    return bool(token) and token == session.get("csrf_token")


def _limits():
    """Current min/max text length limits (shared by templates and validation)."""
    return (
        current_app.config.get("MIN_TEXT_LENGTH", 50),
        current_app.config.get("MAX_TEXT_LENGTH", 50000),
    )


def _render_index(**kwargs):
    """Render the home page with CSRF token and length limits always present."""
    min_length, max_length = _limits()
    return render_template(
        "index.html",
        csrf_token=_get_csrf_token(),
        min_length=min_length,
        max_length=max_length,
        **kwargs,
    )


@main_bp.route('/')
def home():
    return _render_index()


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
        if not _csrf_valid():
            flash("Invalid or missing CSRF token. Please refresh and try again.", "danger")
            return _render_index(), 400

        model = get_predictor()
        if model is None or not model.is_loaded():
            flash('System error: Model not loaded. Please contact administrator.', 'danger')
            return _render_index()

        news_text = request.form.get('news_input', '').strip()

        min_length, max_length = _limits()
        validation_error = validate_news_text(
            news_text,
            min_length=min_length,
            max_length=max_length,
        )
        if validation_error:
            flash(validation_error, 'warning')
            return _render_index()

        current_app.logger.info(f'Processing prediction request ({len(news_text)} chars)')

        try:
            result, confidence = model.predict(news_text)
        except ValueError as e:
            current_app.logger.warning(f'Invalid input: {e}')
            flash(f'Invalid input: {str(e)}', 'warning')
            return _render_index()
        except RuntimeError as e:
            current_app.logger.error(f'Prediction error: {e}')
            flash('Prediction failed. Please try again.', 'danger')
            return _render_index()

        current_app.logger.info(f'Prediction: {result} (confidence: {confidence:.2%})')
        save_prediction(result, confidence, "single", news_text, "ok")
        prediction_text = f'Prediction: {result} (Confidence: {confidence:.2%})'
        prediction_class = 'is-real' if result == 'Real News' else 'is-fake'
        return _render_index(prediction_text=prediction_text, prediction_class=prediction_class)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in predict: {e}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return _render_index()


def validate_input(text: str) -> Optional[str]:
    return validate_news_text(text)


PER_PAGE = 20


@main_bp.route("/history", methods=["GET"])
def history_page():
    label = request.args.get("label")
    if label not in ("Real News", "Fake News", None, ""):
        label = None
    if label == "":
        label = None

    q = (request.args.get("q") or "").strip()
    if len(q) > 100:
        q = q[:100]

    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    if page > 10000:
        page = 10000

    offset = (page - 1) * PER_PAGE
    items = list_predictions(limit=PER_PAGE, offset=offset, label=label, search=q or None)
    total = count_predictions(label, search=q or None)
    pages = (total + PER_PAGE - 1) // PER_PAGE if total else 1

    return render_template(
        "history.html",
        items=items,
        page=page,
        pages=pages,
        total=total,
        label=label or "",
        q=q,
        csrf_token=_get_csrf_token(),
    )


@main_bp.route("/history/<int:pid>", methods=["GET"])
def history_detail(pid):
    item = get_prediction(pid)
    if not item:
        flash("Prediction not found.", "warning")
        return redirect(url_for("main.history_page"))
    return render_template("history_detail.html", item=item)


@main_bp.route("/history/clear", methods=["POST"])
def history_clear():
    """Clear history. Deletion happens only when the confirmation field is present.

    The history page submits this form through a confirmation dialog (JS) or
    renders a confirmation step (no JS), so a single accidental click can
    never delete records.
    """
    if not _csrf_valid():
        flash("Invalid or missing CSRF token.", "danger")
        return redirect(url_for("main.history_page"))

    confirmed = request.form.get("confirm") == "1"
    if not confirmed:
        # First step: show an explicit confirmation page (works without JS).
        return render_template("history_confirm.html", csrf_token=_get_csrf_token())

    ok = clear_all()
    if ok:
        flash("History cleared.", "success")
    else:
        flash("Could not clear history.", "danger")
    return redirect(url_for("main.history_page"))


def _render_batch(**kwargs):
    """Render the batch upload page with CSRF token and effective limits."""
    return render_template(
        "batch.html",
        csrf_token=_get_csrf_token(),
        batch_max_rows=current_app.config.get("BATCH_MAX_ROWS", 1000),
        batch_max_file_mb=current_app.config.get("BATCH_MAX_FILE_SIZE", 5 * 1024 * 1024) // (1024 * 1024),
        **kwargs,
    )


@main_bp.route("/batch", methods=["GET"])
def batch_form():
    return _render_batch()


@main_bp.route("/batch", methods=["POST"])
def batch_process():
    if not _csrf_valid():
        flash("Invalid or missing CSRF token. Please refresh and try again.", "danger")
        return _render_batch(), 400

    if "file" not in request.files:
        flash("No file uploaded.", "danger")
        return _render_batch()

    f = request.files["file"]
    if not f or not f.filename:
        flash("No file selected.", "danger")
        return _render_batch()

    filename = f.filename.lower()
    if not (filename.endswith(".csv") or filename.endswith(".txt")):
        flash("Unsupported file type. Please upload a CSV or TXT file.", "danger")
        return _render_batch()

    data = f.read()
    max_size = current_app.config.get("BATCH_MAX_FILE_SIZE", 5 * 1024 * 1024)
    if len(data) == 0:
        flash("Uploaded file is empty.", "danger")
        return _render_batch()
    if len(data) > max_size:
        flash(f"File too large. Maximum {max_size // (1024*1024)} MB allowed.", "danger")
        return _render_batch()

    try:
        if filename.endswith(".csv"):
            articles = parse_csv_bytes(data)
        else:
            articles = parse_txt_bytes(data)
    except Exception as exc:
        current_app.logger.warning("Batch file parse failed: %s", exc)
        flash("Could not parse file. Please check the format and try again.", "danger")
        return _render_batch()

    max_rows = current_app.config.get("BATCH_MAX_ROWS", 1000)
    if len(articles) == 0:
        flash("No articles found in file.", "danger")
        return _render_batch()
    if len(articles) > max_rows:
        flash(f"Too many rows. Maximum {max_rows} articles allowed.", "danger")
        return _render_batch()

    model = get_predictor()
    if model is None or not model.is_loaded():
        flash("Model not loaded. Please try again later.", "danger")
        return _render_batch()

    min_length, max_length = _limits()
    results = process_articles(
        articles,
        model,
        min_length=min_length,
        max_length=max_length,
    )

    csv_bytes = results_to_csv(results)
    import base64
    session["batch_csv"] = base64.b64encode(csv_bytes).decode("ascii")
    session["batch_filename"] = "predictions.csv"

    save_batch(results, "batch")

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = len(results) - ok
    real_count = sum(1 for r in results if r["prediction"] == "Real News")
    fake_count = sum(1 for r in results if r["prediction"] == "Fake News")
    preview = results[:20]

    return render_template(
        "batch_results.html",
        total=len(results),
        successful=ok,
        failed=failed,
        real_count=real_count,
        fake_count=fake_count,
        preview=preview,
        preview_count=len(preview),
    )


@main_bp.route("/batch/download", methods=["GET"])
def batch_download():
    import base64
    b64 = session.get("batch_csv")
    if not b64:
        flash("No batch results available. Please upload a file first.", "warning")
        return redirect(url_for("main.batch_form"))
    data = base64.b64decode(b64)
    from flask import Response
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=predictions.csv"},
    )
