"""UI/UX sprint coverage: layout, probability mapping, batch, history, feedback, a11y.

These tests exercise server-rendered markup and API contracts. They do not claim
browser-level rendering (layout/JS behavior) — only what the Flask app returns.
"""

import io
import re

import pytest

from core.config import BASE_DIR
from core.utils import history as history_utils

REAL_TEXT = (
    "The Reserve Bank of India announced that the repo rate will remain unchanged "
    "after the latest Monetary Policy Committee meeting held this week."
)


# --------------------------------------------------------------------------
# Phase 1 — shared layout, navigation, titles
# --------------------------------------------------------------------------

ALL_PAGES = ["/", "/batch", "/history"]


def test_single_document_and_shared_layout_on_all_pages(client):
    for url in ALL_PAGES:
        html = client.get(url).data.decode()
        assert html.lower().count("<!doctype html>") == 1, url
        assert html.count('rel="stylesheet"') == 1, url
        assert html.count('class="site-header"') == 1, url
        assert html.count('class="site-footer"') == 1, url
        assert 'class="skip-link"' in html, url
        assert "favicon.svg" in html, url


def test_active_navigation_marks_current_page(client):
    home = client.get("/").data.decode()
    batch = client.get("/batch").data.decode()
    hist = client.get("/history").data.decode()
    assert home.count('aria-current="page"') == 1
    assert batch.count('aria-current="page"') == 1
    assert hist.count('aria-current="page"') == 1
    assert re.search(r'is-active"[^>]*aria-current="page"[^>]*>\s*Home', home)
    assert re.search(r'is-active"[^>]*aria-current="page"[^>]*>\s*Batch', batch)
    assert re.search(r'is-active"[^>]*aria-current="page"[^>]*>\s*History', hist)


def test_history_detail_keeps_history_nav_active(client):
    pid = history_utils.save_prediction("Real News", 0.9, "single", "detail nav test", "ok")
    html = client.get(f"/history/{pid}").data.decode()
    assert re.search(r'is-active"[^>]*aria-current="page"[^>]*>\s*History', html)


def test_page_titles_are_descriptive(client):
    assert "Check an article" in client.get("/").data.decode()
    assert "Batch Prediction" in client.get("/batch").data.decode()
    assert "Prediction History" in client.get("/history").data.decode()


def test_flash_message_rendered_once(client):
    resp = client.post("/predict", data={"news_input": ""})
    html = resp.data.decode()
    assert html.count("Please enter some news text") == 1


# --------------------------------------------------------------------------
# Phase 2 — probability mapping, explanation payloads
# --------------------------------------------------------------------------


def test_probabilities_match_model_class_order(client):
    resp = client.post("/api/predict", json={"text": REAL_TEXT})
    assert resp.status_code == 200
    data = resp.get_json()

    probs = data.get("probabilities")
    if probs is None:
        pytest.skip("Runtime model does not expose probabilities in this environment")

    # Both classes present, keyed by label (never positional)
    assert set(probs) == {"Real News", "Fake News"}
    for value in probs.values():
        assert 0.0 <= value <= 1.0
    assert abs(sum(probs.values()) - 1.0) < 1e-6

    # The predicted label must be the highest-probability class
    winner = max(probs, key=probs.get)
    assert winner == data["prediction"]
    # Binary model: confidence equals the probability of the predicted class
    assert abs(probs[winner] - data["confidence"]) < 1e-9


def test_api_predict_persists_history_and_returns_id(client):
    resp = client.post("/api/predict", json={"text": REAL_TEXT})
    data = resp.get_json()
    pid = data.get("prediction_id")
    assert isinstance(pid, int)
    row = history_utils.get_prediction(pid)
    assert row is not None
    assert row["label"] == data["prediction"]


def test_invalid_probabilities_are_omitted_from_payload(client, monkeypatch):
    from core.utils import model_loader

    class FakeModel:
        def is_loaded(self):
            return True

        def predict(self, text):
            return "Real News", 0.9

        def predict_proba(self, text):
            return {"Real News": float("nan"), "Fake News": 0.1}

        def explain(self, text, top_k=5):
            return {"supporting": [], "opposing": [], "note": "empty-state note"}

    monkeypatch.setattr(model_loader, "_predictor", FakeModel())
    resp = client.post("/api/predict", json={"text": REAL_TEXT})
    data = resp.get_json()
    assert data["success"] is True
    assert "probabilities" not in data
    # explanation payload with empty directions is still returned for the UI empty state
    assert data["explanation"]["supporting"] == []
    assert data["explanation"]["opposing"] == []


def test_probabilities_out_of_range_are_omitted(client, monkeypatch):
    from core.utils import model_loader

    class FakeModel:
        def is_loaded(self):
            return True

        def predict(self, text):
            return "Real News", 0.9

        def predict_proba(self, text):
            return {"Real News": 1.4, "Fake News": -0.4}

    monkeypatch.setattr(model_loader, "_predictor", FakeModel())
    resp = client.post("/api/predict", json={"text": REAL_TEXT})
    assert "probabilities" not in resp.get_json()


# --------------------------------------------------------------------------
# Phase 3 — batch UX and result summary
# --------------------------------------------------------------------------


def test_batch_upload_page_has_accessible_dropzone(client):
    html = client.get("/batch").data.decode()
    assert 'id="dropzone"' in html
    assert 'type="file"' in html
    assert 'accept=".csv,.txt"' in html
    assert 'aria-labelledby="dropzone-label"' in html
    assert 'id="uploading"' in html
    assert "aria-busy" not in html  # busy state is applied only while submitting
    assert "MB" in html and "articles per file" in html


def test_batch_results_counts_are_consistent(client):
    csv_data = (
        "text\n"
        + REAL_TEXT + "\n"
        + "Scientists confirm that drinking ten cups of coffee every day makes humans immortal according to NASA research.\n"
        + "too short\n"
    )
    resp = client.post(
        "/batch",
        data={"file": (io.BytesIO(csv_data.encode()), "rows.csv")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Batch Results" in html

    values = [int(v) for v in re.findall(r'stat-card__value">(\d+)<', html)]
    total, successful, failed, real, fake = values
    assert total == 3
    assert successful + failed == total
    assert real + fake == successful


def test_batch_results_filter_and_responsive_markup(client):
    csv_data = "text\n" + REAL_TEXT + "\n"
    resp = client.post(
        "/batch",
        data={"file": (io.BytesIO(csv_data.encode()), "rows.csv")},
        content_type="multipart/form-data",
    )
    html = resp.data.decode()
    assert 'id="result-filter"' in html
    assert 'data-filter-scope="#batch-table"' in html
    assert 'class="data-table responsive-table"' in html
    assert 'data-label="real"' in html or 'data-label="failed"' in html
    assert "data-label=\"Prediction\"" in html


def test_batch_rejects_unsupported_extension(client):
    resp = client.post(
        "/batch",
        data={"file": (io.BytesIO(b"data"), "evil.exe")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert b"Unsupported file type" in resp.data


def test_batch_download_without_results_redirects(client):
    resp = client.get("/batch/download")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/batch")


# --------------------------------------------------------------------------
# Phase 4 — history UX: badges, search, pagination, confirmation
# --------------------------------------------------------------------------


def test_history_badges_and_relative_time_markup(client):
    history_utils.save_prediction("Real News", 0.95, "single", "badge markup test article", "ok")
    row = history_utils.list_predictions(limit=1)[0]
    html = client.get("/history").data.decode()
    assert 'badge badge--real' in html
    assert '<time class="js-relative" datetime="' in html
    # exact server-rendered fallback timestamp is present for no-JS clients
    assert "UTC</time>" in html
    assert f"/history/{row['id']}" in html


def test_history_search_filters_rows(client):
    history_utils.save_prediction("Real News", 0.9, "single", "unique-searchtoken budget report", "ok")
    html = client.get("/history?q=unique-searchtoken").data.decode()
    assert "unique-searchtoken" in html
    assert "(1 total)" in html

    empty = client.get("/history?q=no-such-token-xyz").data.decode()
    assert "No predictions match your current filters." in empty


def test_history_pagination_preserves_filters(client):
    for i in range(21):
        history_utils.save_prediction(
            "Real News", 0.9, "single", f"pagination-token article number {i} about markets", "ok"
        )
    html = client.get("/history?label=Real+News&q=pagination-token").data.decode()
    assert "Page 1 of 2" in html
    assert "q=pagination-token" in html
    assert "label=Real" in html


def test_history_empty_state(client):
    history_utils.clear_all()
    html = client.get("/history").data.decode()
    assert "No predictions have been saved yet" in html
    assert 'href="/"' in html


def test_clear_history_requires_confirmation(client):
    history_utils.save_prediction("Fake News", 0.8, "single", "confirm test article", "ok")
    before = history_utils.count_predictions()
    assert before > 0

    # Step 1: POST without the confirm flag must not delete anything
    page = client.post("/history/clear")
    assert page.status_code == 200
    assert b"Clear all prediction history?" in page.data
    assert history_utils.count_predictions() == before

    # Step 2: POST with the confirm flag deletes and redirects
    done = client.post("/history/clear", data={"confirm": "1"})
    assert done.status_code == 302
    assert history_utils.count_predictions() == 0


def test_clear_history_requires_csrf(csrf_client):
    history_utils.save_prediction("Fake News", 0.8, "single", "csrf test article", "ok")
    before = history_utils.count_predictions()

    resp = csrf_client.post("/history/clear", data={"confirm": "1"})
    assert resp.status_code == 302  # rejected, redirected back with an error flash
    assert history_utils.count_predictions() == before

    # With a valid token the same request succeeds
    home = csrf_client.get("/")
    m = re.search(rb'name="csrf_token" value="([^"]+)"', home.data)
    assert m
    token = m.group(1).decode()
    ok = csrf_client.post("/history/clear", data={"csrf_token": token, "confirm": "1"})
    assert ok.status_code == 302
    assert history_utils.count_predictions() == 0


def test_history_page_has_confirmation_dialog_markup(client):
    html = client.get("/history").data.decode()
    assert '<dialog id="clear-dialog"' in html
    assert 'aria-labelledby="clear-dialog-title"' in html
    assert 'id="clear-confirm"' in html


# --------------------------------------------------------------------------
# Phase 6/7 — input accessibility hooks and feedback persistence
# --------------------------------------------------------------------------


def test_home_input_accessibility_hooks(client):
    html = client.get("/").data.decode()
    assert 'for="news_input"' in html
    assert 'aria-describedby="min-hint char-count"' in html
    assert 'id="example-btn"' in html
    assert 'data-min="50"' in html
    assert 'data-max="50000"' in html
    assert 'id="form-status"' in html and 'role="status"' in html
    assert 'aria-labelledby="result-heading"' in html
    assert 'tabindex="-1"' in html
    assert 'id="feedback"' in html
    assert 'data-feedback="helpful"' in html
    assert 'data-feedback="not_helpful"' in html


def test_feedback_roundtrip_and_duplicate_policy(client):
    pid = history_utils.save_prediction("Fake News", 0.7, "single", "feedback test article", "ok")

    first = client.post("/api/feedback", json={"prediction_id": pid, "feedback": "helpful"})
    assert first.status_code == 200
    assert first.get_json()["success"] is True
    assert history_utils.get_prediction(pid)["feedback"] == "helpful"

    # Conflicting duplicate: acknowledged but never overwrites the first value
    second = client.post("/api/feedback", json={"prediction_id": pid, "feedback": "not_helpful"})
    assert second.status_code == 200
    assert second.get_json()["already_recorded"] is True
    assert history_utils.get_prediction(pid)["feedback"] == "helpful"

    # Detail page reflects the stored feedback
    detail = client.get(f"/history/{pid}").data.decode()
    assert "Helpful" in detail


def test_feedback_validation(client):
    assert client.post("/api/feedback", json={}).status_code == 400
    assert client.post("/api/feedback", json={"prediction_id": "abc", "feedback": "helpful"}).status_code == 400
    assert client.post("/api/feedback", json={"prediction_id": 1, "feedback": "maybe"}).status_code == 400
    assert client.post("/api/feedback", json={"prediction_id": 999999, "feedback": "helpful"}).status_code == 404


def test_feedback_requires_csrf(csrf_client):
    pid = history_utils.save_prediction("Fake News", 0.7, "single", "csrf feedback article", "ok")
    resp = csrf_client.post("/api/feedback", json={"prediction_id": pid, "feedback": "helpful"})
    assert resp.status_code == 403
    assert history_utils.get_prediction(pid)["feedback"] is None

    home = csrf_client.get("/")
    token = re.search(rb'name="csrf_token" value="([^"]+)"', home.data).group(1).decode()
    ok = csrf_client.post(
        "/api/feedback",
        json={"prediction_id": pid, "feedback": "helpful"},
        headers={"X-CSRF-Token": token},
    )
    assert ok.status_code == 200
    assert history_utils.get_prediction(pid)["feedback"] == "helpful"


def test_api_info_lists_feedback_endpoint(client):
    data = client.get("/api/info").get_json()
    assert "POST /api/feedback" in data["endpoints"]


# --------------------------------------------------------------------------
# SQLite migration — feedback column added to pre-existing databases
# --------------------------------------------------------------------------


def test_init_db_migrates_old_schema_without_data_loss(tmp_path, monkeypatch):
    import sqlite3

    db_file = tmp_path / "legacy.db"
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            """
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                label TEXT NOT NULL,
                confidence REAL,
                input_type TEXT NOT NULL,
                text_excerpt TEXT,
                model_version TEXT,
                status TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO predictions (timestamp, label, confidence, input_type, text_excerpt, model_version, status) "
            "VALUES ('2024-01-01T00:00:00+00:00', 'Real News', 0.9, 'single', 'legacy row', 'test', 'ok')"
        )

    monkeypatch.setenv("HISTORY_DB_PATH", str(db_file))

    history_utils.init_db()  # must add the feedback column in place, idempotently

    with sqlite3.connect(str(db_file)) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(predictions)")}
    assert "feedback" in cols

    rows = history_utils.list_predictions(limit=5)
    assert len(rows) == 1
    assert rows[0]["text_excerpt"] == "legacy row"
    assert rows[0]["feedback"] is None

    # feedback can be recorded on migrated rows
    pid = rows[0]["id"]
    assert history_utils.set_feedback(pid, "helpful") == "set"
    assert history_utils.get_prediction(pid)["feedback"] == "helpful"

    # running the migration again must be safe
    history_utils.init_db()
    assert history_utils.get_prediction(pid)["feedback"] == "helpful"


# --------------------------------------------------------------------------
# Phase 5/8 — design tokens, dark mode, reduced motion, responsive CSS
# --------------------------------------------------------------------------


def test_stylesheet_defines_design_system():
    css = (BASE_DIR / "static" / "style.css").read_text(encoding="utf-8")
    assert ":root" in css and "--space-4" in css and "--radius" in css
    assert "prefers-color-scheme: dark" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ":focus-visible" in css
    assert "@media (max-width: 720px)" in css
    # no fixed body margin that would break mobile layouts
    assert "body {" in css
    body_block = css.split("body {", 1)[1].split("}", 1)[0]
    assert "margin: 0" in body_block


def _strip_js_comments(js: str) -> str:
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js = re.sub(r"^\s*//.*$", "", js, flags=re.M)
    return js


def test_app_js_uses_safe_dom_apis():
    js = _strip_js_comments((BASE_DIR / "static" / "app.js").read_text(encoding="utf-8"))
    assert "innerHTML" not in js
    assert "insertAdjacentHTML" not in js
    assert "document.write" not in js
    # external scripts only (CSP: default-src 'self' style directives)
    batch_js = _strip_js_comments((BASE_DIR / "static" / "batch.js").read_text(encoding="utf-8"))
    assert "innerHTML" not in batch_js
    history_js = _strip_js_comments((BASE_DIR / "static" / "history.js").read_text(encoding="utf-8"))
    assert "innerHTML" not in history_js
