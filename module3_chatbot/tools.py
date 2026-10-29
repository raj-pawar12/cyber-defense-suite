"""Lets the chatbot call Module 1 (URL engine) and Module 2 (message engine)."""
from __future__ import annotations

import re

from errors import ModelNotReadyError
from module2_message_engine.link_extractor import extract_links

MESSAGE_INTENT = re.compile(
    r"\b(is|are|check|analy[sz]e|verify|scan|review|tell)\b.{0,60}\b(e-?mail|mail|sms|message|text|msg|whatsapp)\b", re.I | re.S)
MIN_MESSAGE_CHARS = 60


def _percent(p: float) -> str:
    return "%d%%" % round(p * 100)


def run_tools(message: str, url_detector_factory, message_detector_factory) -> dict:
    """Return {'cards': [...], 'context': [...]} describing what the detectors found."""
    cards, context = [], []
    wants_message = len(message) >= MIN_MESSAGE_CHARS and (
        message.lower().startswith("/check") or MESSAGE_INTENT.search(message) is not None)

    if wants_message:
        try:
            try:
                url_detector = url_detector_factory()
            except ModelNotReadyError:
                url_detector = None
            result = message_detector_factory().analyze(message, url_detector)
            cards.append({"type": "message", "verdict": result["verdict"], "probability": result["phishing_probability"],
                          "links": [l["link"] for l in result["links"]]})
            signs = "; ".join(r["text"] for r in result["reasons"][:3]) or "no strong warning signs"
            context.append("Message check: verdict %s, phishing probability %s. Signs: %s." % (
                result["verdict"], _percent(result["phishing_probability"]), signs))
            return {"cards": cards, "context": context}
        except ModelNotReadyError:
            context.append("The message detector is not trained yet.")

    links = extract_links(message, limit=3)
    if links:
        try:
            detector = url_detector_factory()
        except ModelNotReadyError:
            return {"cards": cards, "context": context + ["The URL detector is not trained yet."]}
        for link in links:
            try:
                r = detector.analyze(link, explain=False)
            except ValueError:
                continue
            cards.append({"type": "url", "url": link, "verdict": r["verdict"], "probability": r["phishing_probability"]})
            signs = "; ".join(x["text"] for x in r["reasons"][:3]) or "no strong warning signs"
            context.append("URL check for %s: verdict %s, phishing probability %s. Signs: %s." % (
                link, r["verdict"], _percent(r["phishing_probability"]), signs))
    return {"cards": cards, "context": context}
