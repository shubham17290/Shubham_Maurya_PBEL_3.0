"""Evaluate the trained model on a labeled CSV.

Usage:
    python core/scripts/evaluate.py path/to/data.csv [--text-col text] [--label-col label]

The CSV must contain a text column and a binary label column (0=fake, 1=real).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.utils.prediction import ModelPredictor
from core.utils.validation import validate_news_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--text-col", default="text")
    parser.add_argument("--label-col", default="label")
    args = parser.parse_args()

    predictor = ModelPredictor.get_instance()
    predictor.load_models()

    y_true = []
    y_pred = []
    skipped = 0
    with open(args.csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            text = (row.get(args.text_col) or "").strip()
            raw_label = row.get(args.label_col)
            if raw_label is None:
                continue
            try:
                label = int(raw_label)
            except ValueError:
                continue
            if validate_news_text(text) is not None:
                skipped += 1
                continue
            pred_label = 0 if predictor.predict(text)[0] == "Fake News" else 1
            y_true.append(label)
            y_pred.append(pred_label)

    if not y_true:
        print("No valid rows to evaluate.")
        return

    # Metrics without extra deps beyond sklearn
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )

    metrics = {
        "n_samples": len(y_true),
        "skipped": skipped,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
    print(json.dumps(metrics, indent=2))
    print("\n" + classification_report(y_true, y_pred, target_names=["Fake", "Real"]))

    # Merge into metadata.json if present
    meta_path = ROOT / "models" / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {}
    meta["evaluation"] = metrics
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nMetrics written to {meta_path}")


if __name__ == "__main__":
    main()