"""Central paths and settings. Environment variables override the defaults."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models_store"
REPORTS_DIR = ROOT / "reports"
URL_MODEL_PATH = MODELS_DIR / "url_model.joblib"
MESSAGE_MODEL_PATH = MODELS_DIR / "message_model.joblib"
KB_INDEX_PATH = MODELS_DIR / "kb_index.joblib"
DEFAULT_DB_PATH = ROOT / "instance" / "app.db"

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
PLACEHOLDER_KEYS = {"", "your_api_key_here", "paste_your_key_here"}

PHISHING_THRESHOLD = 0.75
SUSPICIOUS_THRESHOLD = 0.45


def verdict_for(probability: float) -> str:
    """Map a phishing probability to a human verdict."""
    if probability >= PHISHING_THRESHOLD:
        return "phishing"
    if probability >= SUSPICIOUS_THRESHOLD:
        return "suspicious"
    return "legitimate"


def load_dotenv_file(path: Path | None = None) -> None:
    """Tiny .env loader (no extra dependency). Real environment variables win."""
    env_path = Path(path) if path else ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return "" if key.lower() in PLACEHOLDER_KEYS else key


def gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL
