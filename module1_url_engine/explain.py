"""Per-prediction explanation by occlusion.

For every feature we replace its value with the training median (a "typical" link)
and measure how much the phishing probability drops. Big drops mean that feature
pushed this link towards phishing. It needs no extra libraries and works with any model.
"""
from __future__ import annotations

import numpy as np

FEATURE_LABELS = {
    "url_length": "Overall address length", "host_length": "Domain name length",
    "path_length": "Path length", "query_length": "Query string length",
    "num_dots": "Number of dots", "num_hyphens_host": "Hyphens in the domain",
    "num_hyphens_url": "Hyphens in the address", "num_underscores": "Underscores",
    "num_digits_url": "Digits in the address", "digit_ratio_url": "Share of digits",
    "num_digits_host": "Digits in the domain", "num_special_chars": "Special characters",
    "has_at": "@ sign present", "has_ip_host": "IP address instead of a domain",
    "is_https": "Uses HTTPS", "num_subdomains": "Number of subdomains",
    "has_port": "Non-standard port", "path_depth": "Folder depth",
    "double_slash_in_path": "Double slash in path", "suspicious_word_count": "Pressure words (login, verify...)",
    "brand_mismatch": "Brand name on the wrong domain", "is_shortener": "Link shortener",
    "risky_tld": "Risky domain ending", "free_hosting": "Free hosting service",
    "host_entropy": "Random-looking domain", "url_entropy": "Random-looking address",
    "num_percent_encoded": "Percent-encoded characters", "has_punycode": "Punycode (xn--)",
    "longest_label_len": "Longest domain part", "num_query_params": "Number of query parameters",
    "suspicious_extension": "Script or file extension",
}


def top_contributions(model, feature_names, feats: dict, medians, k: int = 5, min_effect: float = 0.02):
    """Return the k features that most changed the phishing probability for this link."""
    base = np.array([[feats[n] for n in feature_names]], dtype=float)
    medians = np.asarray(medians, dtype=float)
    variants = np.repeat(base, len(feature_names), axis=0)
    for i in range(len(feature_names)):
        variants[i, i] = medians[i]
    p_base = float(model.predict_proba(base)[0][1])
    p_var = model.predict_proba(variants)[:, 1]
    out = []
    for i, name in enumerate(feature_names):
        effect = p_base - float(p_var[i])
        if abs(effect) >= min_effect:
            out.append({
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "value": round(float(base[0, i]), 3),
                "effect": round(effect, 3),
                "direction": "raises risk" if effect > 0 else "lowers risk",
            })
    out.sort(key=lambda r: abs(r["effect"]), reverse=True)
    return out[:k]
