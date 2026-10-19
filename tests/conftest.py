import os
import sys
import tempfile

# Ensure project root is importable (tests/ -> project root is one level up)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

# Isolate the prediction-history database: tests must never touch history.db
_tmp_history_dir = tempfile.mkdtemp(prefix="fnd-history-tests-")
os.environ.setdefault("HISTORY_DB_PATH", os.path.join(_tmp_history_dir, "history.db"))

import pytest  # noqa: E402  (imports must follow sys.path/env setup above)
from app import create_app  # noqa: E402


@pytest.fixture
def app():
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_client(app):
    """Test client for an app with CSRF protection enabled."""
    app.config["CSRF_ENABLED"] = True
    return app.test_client()
