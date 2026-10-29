"""Lazily loads the models once and shares them between requests."""
from __future__ import annotations

import threading

from errors import ModelNotReadyError
from module1_url_engine.predict import URLDetector
from module2_message_engine.predict import MessageDetector
from module3_chatbot.chat_service import ChatService
from module3_chatbot.gemini_client import GeminiClient
from module3_chatbot.retriever import Retriever


class Services:
    def __init__(self):
        self._lock = threading.Lock()
        self._url = self._message = self._retriever = self._chat = None
        self.gemini = GeminiClient()

    def url_detector(self) -> URLDetector:
        with self._lock:
            if self._url is None:
                self._url = URLDetector()
            return self._url

    def message_detector(self) -> MessageDetector:
        with self._lock:
            if self._message is None:
                self._message = MessageDetector()
            return self._message

    def retriever(self) -> Retriever:
        with self._lock:
            if self._retriever is None:
                self._retriever = Retriever()
            return self._retriever

    def chat(self) -> ChatService:
        retriever = self.retriever()
        with self._lock:
            if self._chat is None:
                self._chat = ChatService(retriever, self.gemini, self.url_detector, self.message_detector)
            return self._chat

    def status(self) -> dict:
        ready = {}
        for name, loader in (("url", self.url_detector), ("message", self.message_detector), ("knowledge_base", self.retriever)):
            try:
                loader()
                ready[name] = True
            except ModelNotReadyError:
                ready[name] = False
        return ready
