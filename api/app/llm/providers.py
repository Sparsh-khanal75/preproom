"""LLM providers. All free options: local Ollama (default), any OpenAI-compatible free tier, or a
deterministic mock used by tests and the offline demo."""

from __future__ import annotations

import json
import re
from typing import Protocol

import httpx

from ..config import Settings, get_settings


class LLMError(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str

    async def chat(self, messages: list[dict[str, str]], *, json_mode: bool = False, temperature: float = 0.2) -> str: ...


class OllamaProvider:
    def __init__(self, s: Settings):
        self.url, self.model, self.timeout = s.ollama_url.rstrip("/"), s.ollama_model, s.llm_timeout
        self.name = f"ollama:{self.model}"

    async def chat(self, messages, *, json_mode=False, temperature=0.2) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 4096},
        }
        if json_mode:
            body["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.post(f"{self.url}/api/chat", json=body)
                r.raise_for_status()
                return r.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise LLMError(f"ollama: {type(e).__name__}: {e}") from e


class OpenAICompatibleProvider:
    """Works with free tiers such as Groq or a local llama.cpp / LM Studio server."""

    def __init__(self, s: Settings):
        self.base, self.key, self.model, self.timeout = (
            s.openai_base_url.rstrip("/"),
            s.openai_api_key,
            s.openai_model,
            s.llm_timeout,
        )
        self.name = f"openai-compatible:{self.model}"

    async def chat(self, messages, *, json_mode=False, temperature=0.2) -> str:
        body = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.post(f"{self.base}/chat/completions", json=body, headers=headers)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            raise LLMError(f"openai-compatible: {type(e).__name__}: {e}") from e


class MockProvider:
    """Deterministic stand-in so every feature works (and is testable) with no model installed.

    It recognises the task tag that our prompts put in the system message and produces a
    plausible, rule-derived reply. It is clearly labelled as `mock` in every report.
    """

    name = "mock"

    async def chat(self, messages, *, json_mode=False, temperature=0.2) -> str:
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        data = _extract_data(user)
        if "[task:follow_up]" in system:
            topic = data.get("topic", "that")
            if data.get("reason") == "short":
                return f"Could you tell me more about your {topic}?"
            return f"Can you be more specific about your {topic}, with a name, a number or a date?"
        if "[task:judge]" in system:
            answer = data.get("answer", "")
            words = len(answer.split())
            specifics = len(re.findall(r"\b\d[\d,.]*\b|\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+", answer))
            return json.dumps(
                {
                    "relevance": 8 if words >= 30 else 5,
                    "relevance_reason": "Mock judge: rates longer answers as more complete.",
                    "specificity": min(10, 3 + 2 * specifics),
                    "language": 7,
                    "corrections": [],
                    "contradictions": [],
                    "strength": "Answered the question directly." if words >= 15 else "Stayed calm.",
                    "improvement": (
                        "Answer in more depth: aim for three or four sentences."
                        if words < 30
                        else "Add one concrete example with a number or a name."
                        if specifics < 2
                        else "Good detail. Lead with your direct answer in the first sentence."
                    ),
                }
            )
        return "OK"


def _extract_data(text: str) -> dict:
    m = re.search(r"<data>\s*(\{.*\})\s*</data>", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except ValueError:
        return {}


def get_provider(s: Settings | None = None) -> LLMProvider:
    s = s or get_settings()
    if s.llm_provider == "ollama":
        return OllamaProvider(s)
    if s.llm_provider == "openai_compatible":
        return OpenAICompatibleProvider(s)
    return MockProvider()
