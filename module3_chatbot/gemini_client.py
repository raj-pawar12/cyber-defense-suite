
"""Google Gemini client using the official Google GenAI SDK."""
from __future__ import annotations

import time

from google import genai
from google.genai import types

from config import gemini_api_key, gemini_model

MAX_HISTORY = 6
MAX_TURN_CHARS = 1500


class GeminiError(RuntimeError):
    """A safe error message for Gemini API failures."""


class GeminiClient:
    def __init__(self, timeout: int = 90):
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(gemini_api_key())

    @property
    def model(self) -> str:
        return gemini_model()

    @staticmethod
    def _contents(history, user_text: str) -> list:
        """Convert conversation history to Gemini chat contents."""
        turns = []

        for item in (history or [])[-MAX_HISTORY:]:
            role = "model" if item.get("role") == "assistant" else "user"
            text = str(item.get("content", ""))[:MAX_TURN_CHARS].strip()

            if text:
                turns.append({
                    "role": role,
                    "parts": [{"text": text}],
                })

        turns.append({
            "role": "user",
            "parts": [{"text": user_text}],
        })

        # Gemini conversations must start with a user turn.
        while turns and turns[0]["role"] != "user":
            turns.pop(0)

        # Merge consecutive turns with the same role.
        merged = []
        for turn in turns:
            if merged and merged[-1]["role"] == turn["role"]:
                merged[-1]["parts"][0]["text"] += (
                    "\n" + turn["parts"][0]["text"]
                )
            else:
                merged.append(turn)

        return merged



    def generate(
        self,
        system_prompt: str,
        history,
        user_text: str,
        max_output_tokens: int = 700,
        temperature: float = 0.4,
        **options,
    ) -> str:
        key = gemini_api_key()

        if not key:
            raise GeminiError("No GEMINI_API_KEY is configured.")

        try:
            client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(timeout=15000),
            )

            response = client.models.generate_content(
                model=self.model,
                contents=self._contents(history, user_text),
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )

            answer = (response.text or "").strip()

            if not answer:
                raise GeminiError("The AI returned an empty answer.")

            return answer

        except GeminiError:
            raise
        except Exception as exc:
            raise GeminiError(
                "Gemini request failed (%s)." % type(exc).__name__
            ) from None
