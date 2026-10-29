"""Train, compare and evaluate URL classifiers.

    python -m module1_url_engine.train                  # uses module1_url_engine/data/urls.csv
    python -m module1_url_engine.train --data real.csv  # CSV with columns: url,label (1 = phishing)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from config import REPORTS_DIR, URL_MODEL_PATH

from .features import FEATURE_NAMES, feature_vector

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "data" / "urls.csv"
SEED = 42


def feature_candidates() -> dict:
    return {
        "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        "Decision Tree": DecisionTreeClassifier(max_depth=12, random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=SEED),
        "Hist Gradient Boosting": HistGradientBoostingClassifier(random_state=SEED),
    }


def char_ngram_model():
    """Compared against the feature models, but not deployed (it reads raw characters)."""
    return make_pipeline(
        TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=3, sublinear_tf=True, max_features=60000),
        LogisticRegression(max_iter=2000),
    )


def load_dataset(path: Path):
    df = pd.read_csv(path)
    if not {"url", "label"} <= set(df.columns):
        raise ValueError("The CSV must have the columns: url,label")
    df = df.dropna(subset=["url", "label"]).drop_duplicates(subset="url")
    urls, rows, labels, skipped = [], [], [], 0
    for url, label in zip(df["url"].astype(str), df["label"].astype(int)):
        try:
            rows.append(feature_vector(url))
        except ValueError:  # e.g. malformed IPv6 brackets in a real-world dataset
            skipped += 1
            continue
        urls.append(url)
        labels.append(label)
    if len(set(labels)) < 2:
        raise ValueError("The dataset needs both phishing (1) and legitimate (0) rows.")
    return np.array(urls, dtype=object), np.array(rows, dtype=float), np.array(labels), skipped


def _save_plots(model, X_test, y_test, proba, pred, best_name, auc, reports_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay(confusion_matrix(y_test, pred), display_labels=["Legitimate", "Phishing"]).plot(
        ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Confusion matrix - %s" % best_name)
    fig.tight_layout()
    fig.savefig(reports_dir / "confusion_matrix.png", dpi=150)
    plt.close(fig)

    fpr, tpr, _ = roc_curve(y_test, proba)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.plot(fpr, tpr, label="AUC = %.3f" % auc)
    ax.plot([0, 1], [0, 1], "--", color="grey")
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curve")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(reports_dir / "roc_curve.png", dpi=150)
    plt.close(fig)

    final = model[-1] if hasattr(model, "steps") else model
    imp = getattr(final, "feature_importances_", None)
    if imp is None and hasattr(final, "coef_"):
        imp = np.abs(final.coef_[0])
    if imp is None:
        imp = permutation_importance(model, X_test, y_test, n_repeats=3, random_state=SEED).importances_mean
    order = np.argsort(imp)[-15:]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.barh([FEATURE_NAMES[i] for i in order], np.asarray(imp)[order], color="#1e3a8a")
    ax.set_title("Top 15 features")
    fig.tight_layout()
    fig.savefig(reports_dir / "feature_importance.png", dpi=150)
    plt.close(fig)


def run_training(data_path=None, out_path=None, reports_dir=None, verbose: bool = True) -> dict:
    log = print if verbose else (lambda *a, **k: None)
    data_path = Path(data_path) if data_path else DEFAULT_DATA
    out_path = Path(out_path) if out_path else URL_MODEL_PATH
    reports_dir = Path(reports_dir) if reports_dir else REPORTS_DIR / "url"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    urls, X, y, skipped = load_dataset(data_path)
    log("[url] %d links (%d phishing), %d features, %d skipped" % (len(y), int(y.sum()), X.shape[1], skipped))
    idx_train, idx_test = train_test_split(np.arange(len(y)), test_size=0.2, stratify=y, random_state=SEED)
    X_train, X_test, y_train, y_test = X[idx_train], X[idx_test], y[idx_train], y[idx_test]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    comparison = {}
    for name, model in feature_candidates().items():
        s = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1", n_jobs=-1)
        comparison[name] = {"cv_f1_mean": float(s.mean()), "cv_f1_std": float(s.std()), "deployed": False}
        log("[url]   %-24s CV F1 = %.4f" % (name, s.mean()))

    best_name = max(comparison, key=lambda n: comparison[n]["cv_f1_mean"])
    comparison[best_name]["deployed"] = True
    model = feature_candidates()[best_name].fit(X_train, y_train)

    char_name = "Char n-gram TF-IDF + LR"
    s = cross_val_score(char_ngram_model(), urls[idx_train], y_train, cv=cv, scoring="f1", n_jobs=-1)
    char_fit = char_ngram_model().fit(urls[idx_train], y_train)
    comparison[char_name] = {
        "cv_f1_mean": float(s.mean()), "cv_f1_std": float(s.std()), "deployed": False,
        "test_f1": float(f1_score(y_test, char_fit.predict(urls[idx_test]))),
    }
    log("[url]   %-24s CV F1 = %.4f (comparison only)" % (char_name, s.mean()))

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    auc = float(roc_auc_score(y_test, proba))
    metrics = {
        "module": "url", "best_model": best_name, "n_train": int(len(y_train)), "n_test": int(len(y_test)),
        "n_features": len(FEATURE_NAMES), "accuracy": accuracy_score(y_test, pred),
        "precision": precision_score(y_test, pred), "recall": recall_score(y_test, pred),
        "f1": f1_score(y_test, pred), "roc_auc": auc,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "model_comparison": comparison, "data_file": data_path.name,
        "sklearn_version": sklearn.__version__,
    }
    metrics = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in metrics.items()}
    (reports_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _save_plots(model, X_test, y_test, proba, pred, best_name, auc, reports_dir)

    joblib.dump({
        "model": model, "feature_names": FEATURE_NAMES, "model_name": best_name,
        "medians": np.median(X_train, axis=0).tolist(), "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }, out_path)
    log("[url] best=%s accuracy=%.4f f1=%.4f auc=%.4f -> %s" % (best_name, metrics["accuracy"], metrics["f1"], auc, out_path.name))
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = ap.parse_args()
    run_training(args.data)


if __name__ == "__main__":
    main()
