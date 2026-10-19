import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    return app.test_client()


def test_explainability_endpoint(client):
    text = "The Reserve Bank of India announced that the repo rate will remain unchanged after the latest Monetary Policy Committee meeting."
    r = client.post("/api/predict", json={"text": text})
    assert r.status_code == 200
    data = r.get_json()
    assert "explanation" in data
    exp = data["explanation"]
    assert "supporting" in exp and "opposing" in exp
    assert isinstance(exp["supporting"], list)


def test_batch_csv(client):
    csv_data = "text\nThe Reserve Bank of India announced repo rate unchanged.\nScientists say coffee makes you immortal according to NASA.\n"
    import io
    r = client.post("/batch", data={"file": (io.BytesIO(csv_data.encode()), "t.csv")}, content_type="multipart/form-data")
    assert r.status_code == 200
    assert b"Batch Results" in r.data
    r2 = client.get("/batch/download")
    assert r2.status_code == 200
    assert "predictions.csv" in r2.headers.get("Content-Disposition", "")


def test_history_flow(client):
    text = "The Reserve Bank of India announced that the repo rate will remain unchanged after the latest Monetary Policy Committee meeting."
    r = client.post("/predict", data={"news_input": text})
    assert r.status_code == 200
    r2 = client.get("/history")
    assert r2.status_code == 200
    assert b"Prediction History" in r2.data
    import re
    m = re.search(rb"/history/(\d+)", r2.data)
    assert m
    pid = m.group(1).decode()
    r3 = client.get(f"/history/{pid}")
    assert r3.status_code == 200
    r4 = client.post("/history/clear")
    assert r4.status_code in (200, 302)


def test_csv_formula_injection_sanitized():
    from utils.batch import sanitize_csv_cell, results_to_csv

    assert sanitize_csv_cell("=SUM(A1:A2)") == "'=SUM(A1:A2)"
    assert sanitize_csv_cell("+1+1") == "'+1+1"
    assert sanitize_csv_cell("-1") == "'-1"
    assert sanitize_csv_cell("@cmd") == "'@cmd"
    # leading whitespace before a dangerous char is still neutralized
    assert sanitize_csv_cell("  =x").startswith("'")
    assert sanitize_csv_cell("\t=evil").startswith("'")
    assert sanitize_csv_cell("normal text") == "normal text"
    assert sanitize_csv_cell("hello, world") == "hello, world"

    # end-to-end: dangerous text becomes quoted with apostrophe
    results = [{"row_id": 1, "text": "=cmd", "prediction": "Real News", "confidence": "0.5", "status": "ok"}]
    out = results_to_csv(results).decode()
    assert "'=cmd" in out


def test_pagination_invalid_values(client):
    for q in ["", "abc", "0", "-1"]:
        url = "/history?page=" + q
        r = client.get(url)
        assert r.status_code == 200
    r = client.get("/history?page=2")
    assert r.status_code == 200
    r = client.get("/history?page=999999")
    assert r.status_code == 200


def test_parse_error_no_leak(client):
    import io
    bad = b"\xff\xfe\x00"  # invalid utf-8-ish
    r = client.post("/batch", data={"file": (io.BytesIO(bad), "bad.csv")}, content_type="multipart/form-data")
    # Should not 500; either 200 flash or 400
    assert r.status_code in (200, 400, 413)
    assert b"Traceback" not in r.data
    assert b"File \"/" not in r.data


def test_upload_size_limits(client):
    import io
    # just below 5MB text file (~4.9MB)
    small = ("a" * 100 + "\n") * 49000
    small = small[: 4 * 1024 * 1024]
    r = client.post("/batch", data={"file": (io.BytesIO(small.encode()), "big.txt")}, content_type="multipart/form-data")
    # may fail validation but should not be 413
    assert r.status_code != 413
    # exceeding effective 6MB request limit
    huge = "a" * (7 * 1024 * 1024)
    r2 = client.post("/batch", data={"file": (io.BytesIO(huge.encode()), "huge.txt")}, content_type="multipart/form-data")
    assert r2.status_code in (400, 413)