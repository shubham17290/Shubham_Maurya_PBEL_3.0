"""Export the trained sklearn model/vectorizer to a NumPy/JSON bundle.

Produces models/np_model/* files that allow inference without scikit-learn.
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model" / "model.pkl"
VECT = ROOT / "model" / "vectorizer.pkl"
OUT_DIR = ROOT / "model" / "np_model"


def main():
    with open(MODEL, "rb") as f:
        model = pickle.load(f)
    with open(VECT, "rb") as f:
        vectorizer = pickle.load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    np.save(OUT_DIR / "coef.npy", model.coef_.astype("float64"))
    np.save(OUT_DIR / "intercept.npy", model.intercept_.astype("float64"))
    np.save(OUT_DIR / "idf.npy", vectorizer.idf_.astype("float64"))

    vocab = {str(k): int(v) for k, v in vectorizer.vocabulary_.items()}
    (OUT_DIR / "vocabulary.json").write_text(
        json.dumps(vocab), encoding="utf-8"
    )

    config = {
        "token_pattern": vectorizer.token_pattern,
        "lowercase": bool(vectorizer.lowercase),
        "ngram_range": list(vectorizer.ngram_range),
        "norm": vectorizer.norm,
        "use_idf": bool(vectorizer.use_idf),
        "smooth_idf": bool(vectorizer.smooth_idf),
        "sublinear_tf": bool(vectorizer.sublinear_tf),
        "classes": [int(c) for c in model.classes_],
    }
    (OUT_DIR / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"Exported NumPy model bundle to {OUT_DIR}")
    print(f"  vocab size: {len(vocab)}")
    print(f"  coef shape: {model.coef_.shape}")


if __name__ == "__main__":
    main()
