# Vercel Deployment Guide

This project deploys the Flask application to Vercel with the Python runtime. The deployment is intentionally limited to runtime code and model artifacts; datasets, documentation, tests, and local caches are excluded.

## Deployment inputs

| Path | Purpose |
|---|---|
| `app.py` | WSGI entrypoint and Flask application factory |
| `core/` | Configuration, routes, utilities, and scripts |
| `templates/` | Flask/Jinja templates |
| `static/` | CSS and browser JavaScript |
| `models/` | Model, vectorizer, metadata, and NumPy inference bundle |
| `requirements.txt` | Production dependencies |
| `vercel.json` | Vercel build and routing configuration |
| `.vercelignore` | Files excluded from the deployment upload |

`vercel.json` uses `@vercel/python` with Python 3.12. Its `includeFiles` list keeps the Flask entrypoint, `core/`, `templates/`, `static/`, and `models/` in the build.

## Exclusions that matter

- `assets/` (including the large training CSV) is excluded from deployment.
- `docs/`, `tests/`, `.git/`, virtual environments, and caches are excluded.
- `.vercelignore` excludes broad `*.json` files for data safety, but explicitly re-includes the required model JSON files:
  - `models/np_model/config.json`
  - `models/np_model/vocabulary.json`
  - `models/metadata.json`

Do not remove those negations. Without them, the NumPy inference backend cannot load.

## Production inference

The default backend is `numpy`, configured by `INFERENCE_BACKEND` in `core/config.py`. It reads the bundle in `models/np_model/` and does not require scikit-learn at runtime.

The scikit-learn backend is optional. To use it:

1. Install `requirements-ml.txt`.
2. Set `INFERENCE_BACKEND=sklearn`.
3. Keep `MODEL_PATH` and `VECTORIZER_PATH` pointed at `models/model.pkl` and `models/vectorizer.pkl`.

## Required Vercel environment

`vercel.json` sets `FLASK_ENV=production`. Production configuration requires a `SECRET_KEY`; set it in the Vercel project environment before deploying. Never commit the secret.

## Local checks before deploying

```bash
python -m pytest -q
python -m ruff check .
python app.py
```

Then check:

```bash
curl http://localhost:5000/api/health
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"The Reserve Bank of India announced its latest monetary policy decision this week."}'
```

## Troubleshooting

- **Model not loaded:** verify `models/np_model/config.json`, `vocabulary.json`, `coef.npy`, `idf.npy`, and `intercept.npy` are present.
- **Build too large:** confirm `assets/` and `docs/` are still excluded.
- **Production startup fails:** confirm `SECRET_KEY` is configured for the Vercel environment.
- **API returns 503:** the model files are missing or unreadable; check the deployment function log.
