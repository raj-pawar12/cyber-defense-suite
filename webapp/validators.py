"""Input validation helpers for the API."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from module1_url_engine.features import normalize_url

HOST_RE = re.compile(r"^(?:(?:[a-z0-9_-]+\.)+[a-z0-9-]{2,}|[0-9a-f:.]+|\d{8,10}|0x[0-9a-f]{6,8})$")


def has_valid_host(url: str) -> bool:
    """True if the URL has no whitespace and a plausible domain name or IP address."""
    if re.search(r"\s", url):
        return False
    try:
        host = urlparse(normalize_url(url)[0]).hostname or ""
    except ValueError:
        return False
    return bool(HOST_RE.match(host.lower()))


def clean_history(raw, limit: int = 10) -> list:
    """Keep only well-formed {role, content} items from the browser-supplied chat history."""
    if not isinstance(raw, list):
        return []
    items = []
    for item in raw[-limit:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
            items.append({"role": item["role"], "content": item["content"][:1500]})
    return items
