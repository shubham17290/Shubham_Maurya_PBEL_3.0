"""SQLite-backed prediction history."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

from config import BASE_DIR


def _db_path() -> Path:
    p = os.environ.get("HISTORY_DB_PATH") or "history.db"
    path = Path(p)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    try:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
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
        conn.commit()
        conn.close()
    except Exception:
        pass


def _model_version() -> str:
    try:
        import json

        meta_path = BASE_DIR / "model" / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return str(meta.get("sklearn_version") or meta.get("model_type") or "unknown")
    except Exception:
        pass
    return "unknown"


def _excerpt(text: str, n: int = 300) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n] + "..."


def save_prediction(label: str, confidence, input_type: str, text: str, status: str = "ok") -> Optional[int]:
    try:
        init_db()
        conn = _connect()
        cur = conn.execute(
            "INSERT INTO predictions (timestamp, label, confidence, input_type, text_excerpt, model_version, status) VALUES (?,?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(),
                label,
                float(confidence) if confidence is not None else None,
                input_type,
                _excerpt(text, int(os.environ.get("HISTORY_EXCERPT_LENGTH", 300))),
                _model_version(),
                status,
            ),
        )
        conn.commit()
        rid = cur.lastrowid
        conn.close()
        return rid
    except Exception:
        return None


def save_batch(results: List[Dict], input_type: str = "batch") -> None:
    try:
        init_db()
        conn = _connect()
        rows = []
        for r in results:
            label = r.get("prediction") or ""
            conf = r.get("confidence")
            try:
                conf_val = float(conf) if conf not in (None, "") else None
            except (ValueError, TypeError):
                conf_val = None
            status = r.get("status") or "ok"
            rows.append(
                (
                    datetime.now(timezone.utc).isoformat(),
                    label if label else "N/A",
                    conf_val,
                    input_type,
                    _excerpt(r.get("text", ""), int(os.environ.get("HISTORY_EXCERPT_LENGTH", 300))),
                    _model_version(),
                    status,
                )
            )
        conn.executemany(
            "INSERT INTO predictions (timestamp, label, confidence, input_type, text_excerpt, model_version, status) VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def list_predictions(limit: int = 20, offset: int = 0, label: Optional[str] = None) -> List[Dict]:
    try:
        init_db()
        conn = _connect()
        if label:
            cur = conn.execute(
                "SELECT * FROM predictions WHERE label = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (label, limit, offset),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM predictions ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def count_predictions(label: Optional[str] = None) -> int:
    try:
        init_db()
        conn = _connect()
        if label:
            cur = conn.execute("SELECT COUNT(*) FROM predictions WHERE label = ?", (label,))
        else:
            cur = conn.execute("SELECT COUNT(*) FROM predictions")
        n = cur.fetchone()[0]
        conn.close()
        return int(n)
    except Exception:
        return 0


def get_prediction(pid: int) -> Optional[Dict]:
    try:
        init_db()
        conn = _connect()
        cur = conn.execute("SELECT * FROM predictions WHERE id = ?", (pid,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def clear_all() -> bool:
    try:
        init_db()
        conn = _connect()
        conn.execute("DELETE FROM predictions")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False