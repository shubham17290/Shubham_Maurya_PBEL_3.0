"""Export metadata about the trained model/vectorizer to models/metadata.json."""

import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model" / "model.pkl"
VECT = ROOT / "model" / "vectorizer.pkl"
OUT = ROOT / "model" / "metadata.json"


def main():
    with open(MODEL, "rb") as f:
        model = pickle.load(f)
    with open(VECT, "rb") as f:
        vectorizer = pickle.load(f)

    try:
        import sklearn
        sklearn_version = sklearn.__version__
    except Exception:
        sklearn_version = "unknown"

    meta = {
        "model_type": type(model).__name__,
        "classes": [int(c) for c in getattr(model, "classes_", [])],
        "n_features": int(getattr(model, "n_features_in_", 0) or 0),
        "vectorizer": type(vectorizer).__name__,
        "vocab_size": len(getattr(vectorizer, "vocabulary_", {})),
        "ngram_range": list(getattr(vectorizer, "ngram_range", (1, 1))),
        "max_features": getattr(vectorizer, "max_features", None),
        "lowercase": getattr(vectorizer, "lowercase", None),
        "sklearn_version": sklearn_version,
    }

    OUT.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
