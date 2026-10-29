"""Lexical feature extraction for phishing URL detection.

Everything here works on the URL *string only*. We never visit the link, so
analysing a malicious URL is safe and fast (no network calls, no WHOIS).
"""
from __future__ import annotations

import ipaddress
import math
import re
from collections import Counter
from urllib.parse import parse_qsl, urlparse

SUSPICIOUS_WORDS = (
    "login", "signin", "sign-in", "verify", "verification", "update", "secure",
    "security", "account", "banking", "confirm", "password", "passwd", "suspend",
    "unlock", "wallet", "billing", "payment", "invoice", "recover", "alert",
    "authenticate", "validate", "support", "helpdesk",
)

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "cutt.ly", "rebrand.ly", "shorturl.at", "tiny.cc",
}

RISKY_TLDS = {
    "xyz", "top", "tk", "ml", "ga", "cf", "gq", "click", "link", "work", "zip",
    "country", "kim", "loan", "men", "party", "review", "science", "stream",
    "cn", "rest", "icu", "buzz", "monster", "cyou",
}

FREE_HOSTS = (
    "000webhostapp.com", "weebly.com", "blogspot.com", "wixsite.com",
    "github.io", "firebaseapp.com", "web.app", "netlify.app", "pages.dev",
    "glitch.me", "herokuapp.com", "godaddysites.com", "webflow.io",
)

# Brands that phishers love to imitate (>= 5 letters so substring match is safe).
BRANDS = (
    "paypal", "google", "amazon", "microsoft", "apple", "facebook", "instagram",
    "netflix", "linkedin", "whatsapp", "dropbox", "flipkart", "paytm",
    "hdfcbank", "icicibank", "outlook", "office365",
)
# Registered-domain labels that legitimately belong to a brand above.
BRAND_ALLOWED_LABELS = {"microsoftonline", "live", "icloud", "amazonaws", "office"}

TWO_LEVEL_SUFFIXES = {
    "co.uk", "ac.uk", "gov.uk", "org.uk", "com.au", "edu.au", "co.in", "ac.in",
    "gov.in", "org.in", "net.in", "co.jp", "com.br", "co.za", "com.cn",
    "com.sg", "co.nz",
}

SUSPICIOUS_EXTENSIONS = (".php", ".exe", ".zip", ".apk", ".scr", ".js", ".jar")
LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "$": "s"})


def normalize_url(url: str) -> tuple[str, bool]:
    """Trim whitespace and add a scheme if missing. Returns (url, scheme_was_assumed)."""
    url = (url or "").strip()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return url, False
    return "https://" + url.lstrip("/"), True


def entropy(text: str) -> float:
    """Shannon entropy in bits per character (random-looking text scores higher)."""
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def registered_domain(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in TWO_LEVEL_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _is_ip_like(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    # Obfuscated forms: 3232235777 (decimal) or 0xC0A80001 (hex)
    return bool(re.fullmatch(r"\d{8,10}|0x[0-9a-fA-F]{6,8}", host))


def _safe_port(parsed) -> int | None:
    try:
        return parsed.port
    except ValueError:
        return None


def split_url(url: str) -> dict:
    """Break a URL into human-readable parts (used by the web UI)."""
    norm, assumed = normalize_url(url)
    p = urlparse(norm)
    host = (p.hostname or "").lower()
    reg = registered_domain(host) if host and not _is_ip_like(host) else host
    subdomain = host[: -len(reg) - 1] if reg and host.endswith("." + reg) else ""
    port = _safe_port(p)
    return {
        "normalized": norm,
        "scheme_assumed": assumed,
        "scheme": p.scheme,
        "userinfo": p.netloc.rsplit("@", 1)[0] if "@" in p.netloc else "",
        "subdomain": subdomain,
        "domain": reg,
        "port": str(port) if port is not None else "",
        "rest": (p.path or "") + (("?" + p.query) if p.query else "") + (("#" + p.fragment) if p.fragment else ""),
    }


def extract_features(url: str) -> dict[str, float]:
    """Turn a URL into a fixed-length dict of numeric features."""
    norm, _ = normalize_url(url)
    p = urlparse(norm)
    host = (p.hostname or "").lower()
    path = p.path or ""
    query = p.query or ""
    low_url = norm.lower()
    is_ip = _is_ip_like(host)
    reg = host if is_ip else registered_domain(host)
    reg_label = reg.split(".")[0] if reg else ""
    subdomain = host[: -len(reg) - 1] if (not is_ip and host.endswith("." + reg)) else ""
    tld = host.rsplit(".", 1)[-1] if "." in host and not is_ip else ""

    digits_url = sum(ch.isdigit() for ch in norm)
    searchable = (host + path + "?" + query).lower()
    words_hit = sum(1 for w in SUSPICIOUS_WORDS if w in searchable)

    userinfo = p.netloc.rsplit("@", 1)[0] if "@" in p.netloc else ""
    text_for_brand = (userinfo + host + path).lower().translate(LEET)
    brand_mismatch = 0
    for brand in BRANDS:
        if brand in text_for_brand and reg_label != brand and reg_label not in BRAND_ALLOWED_LABELS:
            brand_mismatch = 1
            break

    labels = [l for l in host.split(".") if l]
    path_segments = [s for s in path.split("/") if s]

    return {
        "url_length": len(norm),
        "host_length": len(host),
        "path_length": len(path),
        "query_length": len(query),
        "num_dots": norm.count("."),
        "num_hyphens_host": host.count("-"),
        "num_hyphens_url": norm.count("-"),
        "num_underscores": norm.count("_"),
        "num_digits_url": digits_url,
        "digit_ratio_url": digits_url / max(len(norm), 1),
        "num_digits_host": sum(ch.isdigit() for ch in host),
        "num_special_chars": sum(norm.count(c) for c in "?=&%#~+"),
        "has_at": int("@" in norm),
        "has_ip_host": int(is_ip),
        "is_https": int(p.scheme == "https"),
        "num_subdomains": len([s for s in subdomain.split(".") if s]),
        "has_port": int(_safe_port(p) is not None),
        "path_depth": len(path_segments),
        "double_slash_in_path": int("//" in path),
        "suspicious_word_count": words_hit,
        "brand_mismatch": brand_mismatch,
        "is_shortener": int(reg in SHORTENERS),
        "risky_tld": int(tld in RISKY_TLDS),
        "free_hosting": int(any(host == h or host.endswith("." + h) for h in FREE_HOSTS)),
        "host_entropy": entropy(host),
        "url_entropy": entropy(low_url),
        "num_percent_encoded": len(re.findall(r"%[0-9a-fA-F]{2}", norm)),
        "has_punycode": int("xn--" in host),
        "longest_label_len": max((len(l) for l in labels), default=0),
        "num_query_params": len(parse_qsl(query, keep_blank_values=True)),
        "suspicious_extension": int(path.lower().endswith(SUSPICIOUS_EXTENSIONS)),
    }


FEATURE_NAMES = list(extract_features("https://example.com").keys())


def feature_vector(url: str) -> list[float]:
    feats = extract_features(url)
    return [feats[name] for name in FEATURE_NAMES]
