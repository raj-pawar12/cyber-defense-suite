"""Flask application factory for the Cyber Defense Suite."""
from __future__ import annotations

import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from config import DEFAULT_DB_PATH, load_dotenv_file
from . import db
from .services import Services

CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
       "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv_file()
    app = Flask(__name__)
    app.config.update(
       DB_PATH=str(
    os.environ.get("DB_PATH")
    or ("/tmp/app.db" if os.environ.get("VERCEL") else DEFAULT_DB_PATH)
),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
        MAX_TEXT_LENGTH=5000,
        MAX_CHAT_LENGTH=2000,
        RATE_LIMITS={"check": (60, 60), "chat": (20, 60)},
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    if os.environ.get("TRUST_PROXY") == "1":  # set on hosts such as Render so rate limits see the real client IP
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    db.init_db(app)
    app.extensions["services"] = Services()

    from .routes_api import bp as api_bp, limiter
    from .routes_pages import bp as pages_bp
    limiter.reset()
    app.register_blueprint(api_bp)
    app.register_blueprint(pages_bp)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    def _wants_json() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(HTTPException)
    def http_error(exc):
        if exc.code == 413:
            message = "That file is too large (limit 4 MB)."
        else:
            message = exc.description or exc.name
        if _wants_json():
            return jsonify(error=message), exc.code
        return "<h1>%s</h1><p>%s</p><p><a href='/'>Back to the checker</a></p>" % (exc.code, message), exc.code

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        app.logger.exception("Unhandled error")
        if _wants_json():
            return jsonify(error="Something went wrong on the server. Please try again."), 500
        return "<h1>500</h1><p>Something went wrong.</p>", 500

    return app
