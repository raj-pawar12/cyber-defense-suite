"""Orchestrates one chatbot turn: guardrails -> tools -> retrieval -> Gemini (or offline answer)."""
from __future__ import annotations

import re

from errors import ModelNotReadyError

from .gemini_client import GeminiError
from .guardrails import check_message, looks_cyber_related
from .prompts import GREETING_REPLY, OUT_OF_SCOPE_REPLY, SYSTEM_PROMPT
from .tools import run_tools

GREETING = re.compile(r"^\s*(hi|hello|hey|hii+|namaste|good\s+(morning|afternoon|evening)|help|start)\b[\s!.?]*$", re.I)


def _shorten(text: str, limit: int = 650) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind(".\n"))
    return (cut[: end + 1] if end > limit // 2 else cut.rstrip() + "...")


class ChatService:
    def __init__(self, retriever, gemini, url_detector_factory, message_detector_factory):
        self.retriever = retriever
        self.gemini = gemini
        self.url_detector_factory = url_detector_factory
        self.message_detector_factory = message_detector_factory

    def _offline_reply(self, hits: list, tool_context: list) -> str:
        parts = []
        if tool_context:
            parts.append("Here is what my detectors found:\n" + "\n".join("- " + c for c in tool_context))
        if hits:
            parts.append("From my cybersecurity knowledge base (%s):\n\n%s" % (hits[0]["title"], _shorten(hits[0]["text"])))
            if len(hits) > 1 and hits[1]["title"] != hits[0]["title"]:
                parts.append("Related (%s):\n\n%s" % (hits[1]["title"], _shorten(hits[1]["text"], 350)))
        if not parts:
            return OUT_OF_SCOPE_REPLY
        return "\n\n".join(parts)

    def answer(self, message: str, history=None) -> dict:
        message = (message or "").strip()
        base = {"reply": "", "mode": "offline", "sources": [], "cards": [], "notice": ""}

        guard = check_message(message)
        if not guard.allowed:
            return dict(base, reply=guard.refusal, mode="blocked")
        if GREETING.match(message):
            return dict(base, reply=GREETING_REPLY, mode="greeting")

        try:
            tools = run_tools(message, self.url_detector_factory, self.message_detector_factory)
        except Exception:  # a detector problem must never break the chat
            tools = {"cards": [], "context": []}

        query = message
        if len(message.split()) <= 5 and history:
            previous = [m["content"] for m in history if m.get("role") == "user" and m.get("content")]
            if previous:
                query = previous[-1] + " " + message
        try:
            hits = self.retriever.search(query, k=3)
        except ModelNotReadyError:
            hits = []

        sources = [{"n": i + 1, "title": h["title"], "heading": h["heading"]} for i, h in enumerate(hits)]
        result = dict(base, sources=sources, cards=tools["cards"])

        if self.gemini.configured:
            context = []
            if hits:
                context.append("Knowledge base excerpts:\n" + "\n".join(
                    "[%d] %s - %s: %s" % (i + 1, h["title"], h["heading"], h["text"]) for i, h in enumerate(hits)))
            if tools["context"]:
                context.append("Tool results:\n" + "\n".join("- " + c for c in tools["context"]))
            user_turn = ("\n\n".join(context) + "\n\n" if context else "") + "User question: " + message
            try:
                result["reply"] = self.gemini.generate(SYSTEM_PROMPT, history, user_turn)
                result["mode"] = "gemini"
                return result
            except GeminiError as exc:
                result["notice"] = "The AI model is unavailable right now (%s) so this answer comes from the local knowledge base." % exc

        if not hits and not tools["context"] and not looks_cyber_related(message):
            result["reply"] = OUT_OF_SCOPE_REPLY
        else:
            result["reply"] = self._offline_reply(hits, tools["context"])
        if not self.gemini.configured:
            result["notice"] = "Offline mode: add a GEMINI_API_KEY to enable the AI model."
        return result
