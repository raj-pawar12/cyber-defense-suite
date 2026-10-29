"""Makes sure data, models and the knowledge-base index exist and match the installed scikit-learn."""
from __future__ import annotations

import joblib
import sklearn

from config import KB_INDEX_PATH, MESSAGE_MODEL_PATH, URL_MODEL_PATH


def _stale(path, key: str = "sklearn_version") -> bool:
    """True if the artifact is missing, unreadable or was built with another scikit-learn version."""
    if not path.exists():
        return True
    try:
        return joblib.load(path).get(key) != sklearn.__version__
    except Exception:
        return True


def ensure_artifacts(verbose: bool = True) -> None:
    log = print if verbose else (lambda *a, **k: None)
    if _stale(URL_MODEL_PATH):
        from module1_url_engine.generate_data import build_dataset
        from module1_url_engine.train import DEFAULT_DATA, run_training
        if not DEFAULT_DATA.exists():
            import csv
            DEFAULT_DATA.parent.mkdir(parents=True, exist_ok=True)
            with open(DEFAULT_DATA, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["url", "label"])
                writer.writerows(build_dataset(6000, 42))
        log("Training the URL model (about a minute)...")
        run_training(verbose=verbose)
    if _stale(MESSAGE_MODEL_PATH):
        from module2_message_engine.generate_data import build_dataset
        from module2_message_engine.train import DEFAULT_DATA, run_training
        if not DEFAULT_DATA.exists():
            import csv
            DEFAULT_DATA.parent.mkdir(parents=True, exist_ok=True)
            with open(DEFAULT_DATA, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["text", "label"])
                writer.writerows(build_dataset(3000, 42))
        log("Training the message model...")
        run_training(verbose=verbose)
    if _stale(KB_INDEX_PATH):
        from module3_chatbot.ingest import build_index
        log("Building the chatbot knowledge base index...")
        build_index()
