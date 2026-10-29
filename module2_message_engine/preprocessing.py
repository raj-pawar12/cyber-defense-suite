"""Text cleaning used before the message classifier."""
from __future__ import annotations

import re

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
NUM_RE = re.compile(r"\d{4,}")


def clean_text(text: str) -> str:
    """Lower-case and replace links, e-mail addresses and long numbers with placeholder tokens."""
    text = (text or "").lower()
    text = URL_RE.sub(" urltoken ", text)
    text = EMAIL_RE.sub(" emailtoken ", text)
    text = NUM_RE.sub(" numtoken ", text)
    return re.sub(r"\s+", " ", text).strip()
