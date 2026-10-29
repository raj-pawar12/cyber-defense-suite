"""JSON API used by the web pages (and available to any other client)."""
from __future__ import annotations

import json

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from config import REPORTS_DIR
from errors import ModelNotReadyError
from module2_message_engine.link_extractor import extract_links
from module2_message_engine.qr_decoder import QRUnavailable, decode_qr

from . import db
from .ratelimit import RateLimiter
from .validators import clean_history, has_valid_host

bp = Blueprint("api", __name__, url_prefix="/api/v1")
limiter = RateLimiter()
MODULES = ("url", "message")
REPORT_FILES = {"confusion_matrix.png", "roc_curve.png", "feature_importance.png"}


def _services():
    return current_app.extensions["services"]


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _too_many(name: str):
    limit, window = current_app.config["RATE_LIMITS"][name]
    if not limiter.allow("%s:%s" % (name, request.remote_addr or "unknown"), limit, window):
        return jsonify(error="Too many requests. Please wait a moment and try again."), 429
    return None


@bp.errorhandler(ModelNotReadyError)
def _not_ready(exc):
    return jsonify(error=str(exc)), 503


@bp.get("/health")
def health():
    svc = _services()
    return jsonify(status="ok", gemini_configured=svc.gemini.configured,
                   gemini_model=svc.gemini.model if svc.gemini.configured else None, models=svc.status())


@bp.post("/check-url")
def check_url():
    blocked = _too_many("check")
    if blocked:
        return blocked
    url = _body().get("url")
    if not isinstance(url, str) or not url.strip():
        return jsonify(error="Enter a web address to check."), 400
    url = url.strip()
    if len(url) > 2048:
        return jsonify(error="That address is longer than 2048 characters."), 400
    if not has_valid_host(url):
        return jsonify(error="That doesn't look like a web address. Try something like https://example.com."), 400
    result = _services().url_detector().analyze(url)
    result["check_id"] = db.record_check(current_app, "url", url, result["verdict"], result["phishing_probability"])
    return jsonify(result)


@bp.post("/check-message")
def check_message():
    blocked = _too_many("check")
    if blocked:
        return blocked
    text = _body().get("text")
    if not isinstance(text, str) or len(text.strip()) < 3:
        return jsonify(error="Paste the email or SMS text you want to check."), 400
    text = text.strip()
    limit = current_app.config["MAX_TEXT_LENGTH"]
    if len(text) > limit:
        return jsonify(error="That message is longer than %d characters." % limit), 400
    svc = _services()
    try:
        url_detector = svc.url_detector()
    except ModelNotReadyError:
        url_detector = None
    result = svc.message_detector().analyze(text, url_detector)
    result["check_id"] = db.record_check(current_app, "message", db.message_subject(text), result["verdict"],
                                         result["phishing_probability"])
    return jsonify(result)


@bp.post("/check-qr")
def check_qr():
    blocked = _too_many("check")
    if blocked:
        return blocked
    upload = request.files.get("image")
    if upload is None:
        return jsonify(error="Choose an image that contains a QR code."), 400
    try:
        decoded = decode_qr(upload.read())
    except QRUnavailable as exc:
        return jsonify(error=str(exc)), 501
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    if not decoded:
        return jsonify(error="No QR code could be read in that image. Try a clearer, closer picture."), 400
    content = decoded[0]
    svc = _services()
    links = [l for l in extract_links(content, limit=5) if has_valid_host(l)]
    analyses = [svc.url_detector().analyze(l, explain=False) for l in links]
    message = None
    if not analyses:
        message = svc.message_detector().analyze(content, None)
    top = max(analyses, key=lambda a: a["phishing_probability"]) if analyses else message
    check_id = db.record_check(current_app, "qr", content[:200], top["verdict"], top["phishing_probability"])
    return jsonify(decoded=content[:500], links=analyses, message=message, verdict=top["verdict"],
                   phishing_probability=top["phishing_probability"], check_id=check_id)


@bp.post("/chat")
def chat():
    blocked = _too_many("chat")
    if blocked:
        return blocked
    body = _body()
    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify(error="Type a question first."), 400
    message = message.strip()
    limit = current_app.config["MAX_CHAT_LENGTH"]
    if len(message) > limit:
        return jsonify(error="Please keep your question under %d characters." % limit), 400
    return jsonify(_services().chat().answer(message, clean_history(body.get("history"))))


@bp.post("/feedback")
def feedback():
    body = _body()
    kind, rating = body.get("kind"), body.get("rating")
    if kind not in ("url", "message", "qr", "chat") or rating not in (1, -1) or isinstance(rating, bool):
        return jsonify(error="Invalid feedback."), 400
    ref_id = body.get("ref_id")
    ref_id = ref_id if isinstance(ref_id, int) and not isinstance(ref_id, bool) else None
    comment = body.get("comment") if isinstance(body.get("comment"), str) else ""
    db.record_feedback(current_app, kind, rating, ref_id, comment)
    return jsonify(ok=True)


@bp.get("/stats")
def stats():
    return jsonify(db.get_stats(current_app))


@bp.get("/metrics")
def metrics():
    module = request.args.get("module", "url")
    if module not in MODULES:
        return jsonify(error="Unknown module."), 400
    path = REPORTS_DIR / module / "metrics.json"
    if not path.exists():
        return jsonify(error="Metrics not found. Run `python manage.py setup`."), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@bp.get("/reports/<module>/<filename>")
def report_file(module: str, filename: str):
    if module not in MODULES or filename not in REPORT_FILES:
        return jsonify(error="Not found."), 404
    return send_from_directory(REPORTS_DIR / module, filename)
