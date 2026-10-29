"""Train and evaluate the phishing e-mail / SMS classifier.

    python -m module2_message_engine.train
    python -m module2_message_engine.train --data real_messages.csv    # columns: text,label
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC

from config import MESSAGE_MODEL_PATH, REPORTS_DIR

from .preprocessing import clean_text

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "data" / "messages.csv"
SEED = 42


def vectorizer():
    return TfidfVectorizer(preprocessor=clean_text, ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=50000)


def candidates() -> dict:
    return {
        "Logistic Regression": make_pipeline(vectorizer(), LogisticRegression(max_iter=2000)),
        "Naive Bayes": make_pipeline(vectorizer(), MultinomialNB(alpha=0.3)),
        "Linear SVM (calibrated)": make_pipeline(vectorizer(), CalibratedClassifierCV(LinearSVC(), cv=3)),
    }


def run_training(data_path=None, out_path=None, reports_dir=None, verbose: bool = True) -> dict:
    log = print if verbose else (lambda *a, **k: None)
    data_path = Path(data_path) if data_path else DEFAULT_DATA
    out_path = Path(out_path) if out_path else MESSAGE_MODEL_PATH
    reports_dir = Path(reports_dir) if reports_dir else REPORTS_DIR / "message"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    if not {"text", "label"} <= set(df.columns):
        raise ValueError("The CSV must have the columns: text,label")
    df = df.dropna(subset=["text", "label"]).drop_duplicates(subset="text")
    texts = df["text"].astype(str).to_numpy(dtype=object)
    y = df["label"].astype(int).to_numpy()
    if len(set(y)) < 2:
        raise ValueError("The dataset needs both phishing (1) and legitimate (0) rows.")
    log("[message] %d messages (%d phishing)" % (len(y), int(y.sum())))

    X_train, X_test, y_train, y_test = train_test_split(texts, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    comparison = {}
    for name, model in candidates().items():
        s = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1", n_jobs=-1)
        comparison[name] = {"cv_f1_mean": float(s.mean()), "cv_f1_std": float(s.std()), "deployed": False}
        log("[message]   %-26s CV F1 = %.4f" % (name, s.mean()))

    best_name = max(comparison, key=lambda n: comparison[n]["cv_f1_mean"])
    comparison[best_name]["deployed"] = True
    pipeline = candidates()[best_name].fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    auc = float(roc_auc_score(y_test, proba))
    metrics = {
        "module": "message", "best_model": best_name, "n_train": int(len(y_train)), "n_test": int(len(y_test)),
        "n_features": len(pipeline[0].vocabulary_), "accuracy": accuracy_score(y_test, pred),
        "precision": precision_score(y_test, pred), "recall": recall_score(y_test, pred),
        "f1": f1_score(y_test, pred), "roc_auc": auc,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "model_comparison": comparison, "data_file": data_path.name, "sklearn_version": sklearn.__version__,
    }
    metrics = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in metrics.items()}
    (reports_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay(confusion_matrix(y_test, pred, labels=[0, 1]), display_labels=["Legitimate", "Phishing"]).plot(
        ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Confusion matrix - %s" % best_name)
    fig.tight_layout(); fig.savefig(reports_dir / "confusion_matrix.png", dpi=150); plt.close(fig)

    fpr, tpr, _ = roc_curve(y_test, proba)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.plot(fpr, tpr, label="AUC = %.3f" % auc); ax.plot([0, 1], [0, 1], "--", color="grey")
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curve"); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(reports_dir / "roc_curve.png", dpi=150); plt.close(fig)

    # Top words chart from a Logistic Regression view of the same features
    vec = vectorizer(); matrix = vec.fit_transform(X_train)
    lr = LogisticRegression(max_iter=2000).fit(matrix, y_train)
    words = np.array(vec.get_feature_names_out()); coef = lr.coef_[0]
    order = np.concatenate([np.argsort(coef)[:8], np.argsort(coef)[-8:]])
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.barh(words[order], coef[order], color=["#0b7a53" if c < 0 else "#b42318" for c in coef[order]])
    ax.set_title("Words pushing towards legitimate (green) or phishing (red)")
    fig.tight_layout(); fig.savefig(reports_dir / "feature_importance.png", dpi=150); plt.close(fig)

    joblib.dump({"pipeline": pipeline, "model_name": best_name, "sklearn_version": sklearn.__version__,
                 "trained_at": datetime.now(timezone.utc).isoformat()}, out_path)
    log("[message] best=%s accuracy=%.4f f1=%.4f auc=%.4f -> %s" % (best_name, metrics["accuracy"], metrics["f1"], auc, out_path.name))
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = ap.parse_args()
    run_training(args.data)


if __name__ == "__main__":
    main()
