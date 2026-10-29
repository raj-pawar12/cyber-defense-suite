"""HTML pages."""
from __future__ import annotations

from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)


@bp.get("/")
def checker():
    return render_template("checker.html", active="checker")


@bp.get("/message")
def message():
    return render_template("message.html", active="message")


@bp.get("/chat")
def chat():
    return render_template("chat.html", active="chat")


@bp.get("/performance")
def performance():
    return render_template("performance.html", active="performance")
