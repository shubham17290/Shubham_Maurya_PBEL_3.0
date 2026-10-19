"""Batch prediction helpers for CSV/TXT uploads."""

import csv
import io
from typing import List, Dict

TEXT_COLUMNS = {"text", "article", "content", "news", "body", "headline"}


def parse_csv_bytes(data: bytes) -> List[str]:
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader]
    if not rows:
        raise ValueError("CSV file is empty.")

    # Detect header
    first = [c.strip() for c in rows[0]]
    has_header = any(c.lower() in TEXT_COLUMNS for c in first)
    if has_header:
        idx = 0
        for i, c in enumerate(first):
            if c.lower() in TEXT_COLUMNS:
                idx = i
                break
        data_rows = rows[1:]
    else:
        idx = 0
        data_rows = rows

    articles = []
    for r in data_rows:
        if not r:
            articles.append("")
            continue
        val = r[idx] if idx < len(r) else ""
        articles.append(val)
    return articles


def parse_txt_bytes(data: bytes) -> List[str]:
    text = data.decode("utf-8-sig")
    if "\n\n" in text:
        parts = [p.strip() for p in text.split("\n\n")]
    else:
        parts = [ln.strip() for ln in text.splitlines()]
    return [p for p in parts if p != ""] or [""]


def process_articles(articles, predictor, min_length: int, max_length: int) -> List[Dict]:
    results = []
    for i, art in enumerate(articles, start=1):
        art = (art or "").strip()
        if not art:
            results.append({"row_id": i, "text": art, "prediction": "", "confidence": "", "status": "empty row skipped"})
            continue
        from utils.validation import validate_news_text

        err = validate_news_text(art, min_length=min_length, max_length=max_length)
        if err:
            results.append({"row_id": i, "text": art, "prediction": "", "confidence": "", "status": err})
            continue
        try:
            label, conf = predictor.predict(art)
            results.append({"row_id": i, "text": art, "prediction": label, "confidence": f"{conf:.4f}", "status": "ok"})
        except Exception as exc:
            results.append({"row_id": i, "text": art, "prediction": "", "confidence": "", "status": str(exc)})
    return results


def results_to_csv(results: List[Dict]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["row_id", "text", "prediction", "confidence", "status"], quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for r in results:
        row = dict(r)
        if len(row["text"]) > 500:
            row["text"] = row["text"][:500] + "..."
        writer.writerow(row)
    return output.getvalue().encode("utf-8")