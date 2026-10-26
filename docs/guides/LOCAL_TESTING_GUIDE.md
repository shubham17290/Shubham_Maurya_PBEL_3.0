# Local Testing Guide

## Prerequisites

- Python 3.12 (see `.python-version`)
- pip
- A virtual environment is recommended

## Setup

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install the application and test dependencies:

```bash
pip install -r requirements-dev.txt
```

For runtime-only development, `pip install -r requirements.txt` is sufficient. Use `requirements-ml.txt` only when testing the optional scikit-learn backend.

## Run the application

```bash
python app.py
```

The development server listens on `http://localhost:5000` by default. Override `HOST` or `PORT` with environment variables if needed.

## Verify the application

```bash
python -m pytest -q
python -m ruff check .
```

The pytest suite covers the homepage, health check, API metadata, validation, a valid prediction, and 404 handling.

## API checks

```bash
curl http://localhost:5000/api/health
```

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"The Reserve Bank of India announced its latest monetary policy decision this week."}'
```

Expected shape:

```json
{
  "success": true,
  "prediction": "Real News",
  "confidence": 0.7639,
  "confidence_percentage": "76.39%",
  "low_confidence": false,
  "text_length": 83,
  "probabilities": {
    "Fake News": 0.2361,
    "Real News": 0.7639
  }
}
```

The exact prediction and confidence depend on the input and bundled model.

## How startup works

`app.py` provides `create_app()` and exposes `app` for WSGI servers. Blueprints are registered from `core/routes/`. The model is loaded lazily on the first health or prediction request, so the application can start even when model files are temporarily unavailable.

The default backend is NumPy:

- `core/utils/model_loader.py` selects `INFERENCE_BACKEND`.
- `numpy` reads `models/np_model/`.
- `sklearn` reads `models/model.pkl` and `models/vectorizer.pkl`.

## Project layout

```text
app.py                         Flask factory and WSGI entrypoint
core/
  config.py                    Environment configuration
  routes/                      Main page and API blueprints
  scripts/                     Evaluation and model-export tools
  utils/                       Prediction, validation, rate limiting, metrics
models/                        sklearn artifacts and NumPy inference bundle
templates/index.html           Flask page template
static/                        Application CSS and JavaScript
assets/data/                   Local training data
tests/                         pytest suite
docs/                          GitHub Pages site and guides
```

`history.db` is local prediction-history data. It is preserved in the workspace; the current inference endpoints do not read or write it.

## Troubleshooting

### `ModuleNotFoundError: No module named 'flask'`

Activate the virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

### `FileNotFoundError: Missing model file`

Verify the NumPy bundle exists:

```text
models/np_model/config.json
models/np_model/vocabulary.json
models/np_model/coef.npy
models/np_model/idf.npy
models/np_model/intercept.npy
```

For the sklearn backend, verify `models/model.pkl` and `models/vectorizer.pkl` instead.

### `Address already in use`

Change the port:

Windows:

```powershell
$env:PORT=5001
python app.py
```

Linux/macOS:

```bash
PORT=5001 python app.py
```

### `TemplateNotFound: index.html`

Confirm `templates/index.html` exists at the project root, alongside `app.py`. `Flask(__name__)` resolves templates and static files from that root.

### Production startup fails with a missing secret

`FLASK_ENV=production` requires `SECRET_KEY`. Set it in the environment before starting the production server. Do not commit the value.

### API returns 503

The model bundle failed to load. Check the application log for the missing path or parsing error, then rerun the health check.
