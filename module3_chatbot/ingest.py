"""Build the retrieval index from the Markdown files in knowledge_base/."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from config import KB_INDEX_PATH

HERE = Path(__file__).resolve().parent
KB_DIR = HERE / "knowledge_base"
MAX_CHUNK = 900
_WORD = re.compile(r"[a-z0-9]+")


def _stem(word: str) -> str:
    """Very light stemming so 'clicked', 'clicking' and 'clicks' match."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def analyze(text: str) -> list:
    """Tokenizer used by the retrieval index: lower-case, drop stop words, stem, add bigrams."""
    tokens = [_stem(t) for t in _WORD.findall(text.lower()) if t not in ENGLISH_STOP_WORDS]
    return tokens + [a + " " + b for a, b in zip(tokens, tokens[1:])]


def load_documents(kb_dir=None) -> list:
    docs = []
    for path in sorted(Path(kb_dir or KB_DIR).glob("*.md")):
        text = path.read_text(encoding="utf-8-sig")
        title = path.stem.replace("_", " ")
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        docs.append({"title": title, "source": path.name, "text": text})
    return docs


def _split_long(text: str, limit: int = MAX_CHUNK) -> list:
    pieces, current = [], ""
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        if current and len(current) + len(para) + 2 > limit:
            pieces.append(current)
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    if current:
        pieces.append(current)
    return pieces


def chunk_document(doc: dict) -> list:
    """Split a document into chunks at '## ' headings (long sections are split further)."""
    sections, heading, buf = [], "Overview", []
    for line in doc["text"].splitlines():
        if line.startswith("## "):
            if buf:
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = line[3:].strip(), []
        elif not line.startswith("# "):
            buf.append(line)
    if buf:
        sections.append((heading, "\n".join(buf).strip()))
    chunks = []
    for heading, body in sections:
        if not body:
            continue
        for piece in _split_long(body):
            chunks.append({"title": doc["title"], "source": doc["source"], "heading": heading, "text": piece})
    return chunks


def build_index(kb_dir=None, out_path=None) -> dict:
    chunks = []
    for doc in load_documents(kb_dir):
        chunks.extend(chunk_document(doc))
    if not chunks:
        raise ValueError("No knowledge base articles found in %s" % (kb_dir or KB_DIR))
    corpus = ["%s %s %s %s %s" % (c["title"], c["heading"], c["title"], c["heading"], c["text"]) for c in chunks]
    vectorizer = TfidfVectorizer(analyzer=analyze, sublinear_tf=True)
    matrix = vectorizer.fit_transform(corpus)
    out_path = Path(out_path) if out_path else KB_INDEX_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "chunks": chunks, "sklearn_version": sklearn.__version__,
                 "built_at": datetime.now(timezone.utc).isoformat()}, out_path)
    return {"articles": len(load_documents(kb_dir)), "chunks": len(chunks), "path": str(out_path)}


if __name__ == "__main__":
    print(build_index())
