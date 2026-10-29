"""Find the knowledge-base passages most relevant to a question (TF-IDF cosine similarity)."""
from __future__ import annotations

from pathlib import Path

import joblib

from config import KB_INDEX_PATH
from errors import ModelNotReadyError

from .ingest import build_index


class Retriever:
    def __init__(self, path=None, auto_build: bool = True):
        path = Path(path) if path else KB_INDEX_PATH
        if not path.exists():
            if not auto_build:
                raise ModelNotReadyError("Knowledge base index not found. Run `python manage.py setup`.")
            build_index(out_path=path)
        try:
            bundle = joblib.load(path)
            self.vectorizer, self.matrix, self.chunks = bundle["vectorizer"], bundle["matrix"], bundle["chunks"]
        except Exception as exc:
            raise ModelNotReadyError("Knowledge base index could not be loaded (%s). Run `python manage.py setup`."
                                     % type(exc).__name__) from exc

    def search(self, query: str, k: int = 3, min_score: float = 0.08) -> list:
        query = (query or "").strip()
        if not query:
            return []
        scores = (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()
        order = scores.argsort()[::-1][:k]
        hits = []
        for i in order:
            if scores[i] >= min_score:
                chunk = dict(self.chunks[int(i)])
                chunk["score"] = round(float(scores[i]), 3)
                hits.append(chunk)
        return hits
