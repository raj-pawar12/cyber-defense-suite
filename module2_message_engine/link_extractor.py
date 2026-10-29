"""Find links inside an e-mail or SMS so Module 1 can score them."""
from __future__ import annotations

import re

_TLDS = ("com|net|org|in|co|io|xyz|top|tk|ml|ga|cf|gq|info|online|site|click|link|live|me|cc|ru|cn|icu|biz|app|"
         "dev|ly|gl|is|ws|club|shop|store|work")
URL_PATTERN = re.compile(
    r"""(?ix)
    (?:https?://[^\s<>"'\]\)]+)                                   # explicit scheme
    |(?:www\.[^\s<>"'\]\)]+)                                      # www.something
    |(?:\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:%s)\b(?:/[^\s<>"'\]\)]*)?)   # bare domain with known ending
    """ % _TLDS
)
_EMAIL_AT = re.compile(r"[\w.+-]+@$")
TRAILING = ".,;:!?)]}>'\""


def extract_links(text: str, limit: int = 10) -> list:
    """Return unique links found in the text (max `limit`), in order of appearance."""
    found, seen = [], set()
    for match in URL_PATTERN.finditer(text or ""):
        start = match.start()
        # skip the domain part of an e-mail address such as name@example.com
        if start > 0 and text[start - 1] == "@":
            continue
        link = match.group(0).rstrip(TRAILING)
        if len(link) < 4 or link.lower() in seen:
            continue
        seen.add(link.lower())
        found.append(link)
        if len(found) >= limit:
            break
    return found
