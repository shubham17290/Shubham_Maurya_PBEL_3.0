def test_homepage(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Fake News Detection" in resp.data


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code in (200, 503)
    data = resp.get_json()
    assert "status" in data
    assert "model_loaded" in data


def test_api_info(client):
    resp = client.get("/api/info")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Fake News Detection API"
    assert "endpoints" in data


def test_predict_empty_form(client):
    resp = client.post("/predict", data={"news_input": ""})
    assert resp.status_code == 200
    assert b"Please enter" in resp.data or b"warning" in resp.data.lower()


def test_api_predict_missing_text(client):
    resp = client.post("/api/predict", json={})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_api_predict_short_text(client):
    resp = client.post("/api/predict", json={"text": "too short"})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_api_predict_valid(client):
    text = (
        "The Reserve Bank of India announced that the repo rate will remain unchanged "
        "after the latest Monetary Policy Committee meeting held this week."
    )
    resp = client.post("/api/predict", json={"text": text})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["prediction"] in ("Real News", "Fake News")
    assert 0 <= data["confidence"] <= 1


def test_404(client):
    resp = client.get("/this-does-not-exist")
    assert resp.status_code == 404