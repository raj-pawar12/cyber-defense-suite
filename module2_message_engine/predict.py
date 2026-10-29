"""Analyse an e-mail or SMS: text model + every link scored by Module 1."""
from __future__ import annotations

import re
from pathlib import Path

import joblib

from config import MESSAGE_MODEL_PATH, verdict_for
from errors import ModelNotReadyError

from .link_extractor import extract_links

HINT = "Run `python manage.py setup` to train the models."
SAFE_PHRASES = re.compile(r"(do not|don't|never|dont)\s+share[^.]*", re.IGNORECASE)

RULES = [
    ("medium", re.compile(r"\b(urgent|immediately|act now|last warning|final notice|within \d+ hours?|expires? today|right away)\b", re.I),
     "Uses urgency to rush you into acting."),
    ("high", re.compile(r"\b(share|send|enter|provide|confirm|verify|update|submit)\b[^.\n]{0,40}\b(otp|pin|password|cvv|card (number|details)|aadhaar|pan)\b", re.I),
     "Asks you to hand over a secret such as an OTP, PIN, password or card detail."),
    ("medium", re.compile(r"\b(won|winner|lottery|prize|reward|cashback|gift (card|voucher)|refund|free)\b", re.I),
     "Promises money, prizes or rewards."),
    ("medium", re.compile(r"\b(suspend(ed)?|blocked|deactivat\w*|terminat\w*|legal action|arrest|penalty|frozen|freeze|disconnect\w*)\b", re.I),
     "Threatens to block, close or punish your account."),
    ("medium", re.compile(r"\b(attached|attachment|open the (file|document)|enable content|\.exe|\.zip|\.html)\b", re.I),
     "Pushes you to open an attachment or file."),
    ("low", re.compile(r"\b(dear (customer|user|sir|madam|valued))\b", re.I),
     "Uses a generic greeting instead of your name."),
    ("medium", re.compile(r"\b(registration fee|processing fee|pay (a )?small fee|gift cards?)\b", re.I),
     "Asks for an upfront payment or gift cards."),
]


class MessageDetector:
    """Wraps the saved text pipeline."""

    def __init__(self, path=None):
        path = Path(path) if path else MESSAGE_MODEL_PATH
        if not path.exists():
            raise ModelNotReadyError("Message model not found. " + HINT)
        try:
            bundle = joblib.load(path)
            self.pipeline = bundle["pipeline"]
            self.model_name = bundle["model_name"]
        except Exception as exc:
            raise ModelNotReadyError("Message model could not be loaded (%s). %s" % (type(exc).__name__, HINT)) from exc

    def text_probability(self, text: str) -> float:
        return float(self.pipeline.predict_proba([text])[0][1])

    def influential_words(self, text: str, base_p: float, k: int = 6) -> list:
        """Occlusion: remove each word and see how much the phishing probability falls."""
        tokens = []
        for tok in re.findall(r"[A-Za-z']{3,}", text):
            low = tok.lower()
            if low not in tokens:
                tokens.append(low)
        tokens = tokens[:40]
        if not tokens:
            return []
        variants = [re.sub(r"\b%s\b" % re.escape(tok), " ", text, flags=re.IGNORECASE) for tok in tokens]
        probs = self.pipeline.predict_proba(variants)[:, 1]
        out = []
        for tok, p in zip(tokens, probs):
            effect = base_p - float(p)
            if abs(effect) >= 0.01:
                out.append({"word": tok, "effect": round(effect, 3), "direction": "raises risk" if effect > 0 else "lowers risk"})
        out.sort(key=lambda r: abs(r["effect"]), reverse=True)
        return out[:k]

    def analyze(self, text: str, url_detector=None) -> dict:
        text = (text or "").strip()
        p_text = self.text_probability(text)

        links = []
        for link in extract_links(text):
            entry = {"link": link, "analysis": None}
            if url_detector is not None:
                try:
                    entry["analysis"] = url_detector.analyze(link, explain=False)
                except ValueError:
                    entry["analysis"] = None
            links.append(entry)

        worst_link = max((l["analysis"]["phishing_probability"] for l in links if l["analysis"]), default=0.0)
        combined = max(p_text, worst_link)

        scan_text = SAFE_PHRASES.sub(" ", text)
        reasons = [{"severity": sev, "text": msg} for sev, rx, msg in RULES if rx.search(scan_text)]
        for l in links:
            a = l["analysis"]
            if a and a["verdict"] != "legitimate":
                first = a["reasons"][0]["text"] if a["reasons"] else "The address pattern looks risky."
                reasons.append({"severity": "high" if a["verdict"] == "phishing" else "medium",
                                "text": "The link %s looks risky. %s" % (l["link"][:60], first)})
        order = {"high": 0, "medium": 1, "low": 2}
        reasons.sort(key=lambda r: order[r["severity"]])

        return {
            "verdict": verdict_for(combined),
            "phishing_probability": round(combined, 4),
            "text_probability": round(p_text, 4),
            "worst_link_probability": round(worst_link, 4),
            "model": self.model_name,
            "links": links,
            "reasons": reasons,
            "influential_words": self.influential_words(text, p_text),
        }
