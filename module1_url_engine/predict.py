"""Load the trained URL model and analyse a single link."""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from config import URL_MODEL_PATH, verdict_for
from errors import ModelNotReadyError

from .explain import top_contributions
from .features import extract_features, split_url

HINT = "Run `python manage.py setup` to train the models."


def explain_reasons(f: dict, parts: dict) -> list:
    """Plain-English warning signs derived from the features (independent of the model)."""
    out = []

    def add(severity: str, text: str) -> None:
        out.append({"severity": severity, "text": text})

    if f["has_ip_host"]:
        add("high", "The address uses a raw IP number instead of a domain name.")
    if f["has_at"]:
        add("high", "Contains an @ sign. Browsers ignore everything before it, so the real site is the part after it.")
    if f["brand_mismatch"]:
        add("high", "Mentions a well-known brand, but the domain does not belong to that brand.")
    if f["has_punycode"]:
        add("high", "Uses punycode (xn--), which can disguise look-alike characters.")
    if f["is_shortener"]:
        add("medium", "A link shortener hides the real destination.")
    if f["risky_tld"]:
        add("medium", "The domain ending is one that is often used for throwaway sites.")
    if f["free_hosting"]:
        add("medium", "Hosted on a free website service, which anyone can sign up for.")
    if f["suspicious_word_count"] >= 2:
        add("medium", "Contains %d pressure words such as login, verify or secure." % int(f["suspicious_word_count"]))
    elif f["suspicious_word_count"] == 1:
        add("low", "Contains a sensitive word such as login or verify.")
    if f["num_subdomains"] >= 3:
        add("medium", "Has %d subdomain levels, which can bury the real domain." % int(f["num_subdomains"]))
    if f["num_hyphens_host"] >= 3:
        add("medium", "The domain name is stuffed with hyphens.")
    if f["suspicious_extension"]:
        add("medium", "Points to a script or downloadable file type.")
    if f["num_percent_encoded"] >= 3:
        add("low", "Heavy percent-encoding makes the path hard to read.")
    if f["url_length"] > 90:
        add("low", "Very long address (%d characters)." % int(f["url_length"]))
    if f["has_port"]:
        add("low", "Uses a non-standard port number.")
    if not f["is_https"] and not parts["scheme_assumed"]:
        add("low", "Not using HTTPS.")
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(out, key=lambda r: order[r["severity"]])


class URLDetector:
    """Wraps the saved model bundle."""

    def __init__(self, path=None):
        path = Path(path) if path else URL_MODEL_PATH
        if not path.exists():
            raise ModelNotReadyError("URL model not found. " + HINT)
        try:
            bundle = joblib.load(path)
            self.model = bundle["model"]
            self.feature_names = list(bundle["feature_names"])
            self.medians = list(bundle["medians"])
            self.model_name = bundle["model_name"]
        except Exception as exc:  # corrupted file, version mismatch, missing key
            raise ModelNotReadyError("URL model could not be loaded (%s). %s" % (type(exc).__name__, HINT)) from exc

    def analyze(self, url: str, explain: bool = True) -> dict:
        url = (url or "").strip()
        parts = split_url(url)
        feats = extract_features(url)
        row = np.array([[feats[n] for n in self.feature_names]], dtype=float)
        p = float(self.model.predict_proba(row)[0][1])
        result = {
            "url": url,
            "verdict": verdict_for(p),
            "phishing_probability": round(p, 4),
            "model": self.model_name,
            "parts": parts,
            "reasons": explain_reasons(feats, parts),
        }
        if explain:
            result["contributions"] = top_contributions(self.model, self.feature_names, feats, self.medians)
        return result
