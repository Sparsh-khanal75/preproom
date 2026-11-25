import asyncio
import json

import httpx
import pytest
import respx
from sqlalchemy import select

from app import db as dbmod
from app.config import Settings
from app.jobs import handlers, queue
from app.llm.providers import LLMError, MockProvider, OllamaProvider, OpenAICompatibleProvider, get_provider
from app.models import Job


@respx.mock
async def test_ollama_provider_json_mode():
    route = respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": '{"ok": true}'}})
    )
    p = OllamaProvider(Settings(ollama_url="http://ollama.test", ollama_model="qwen2.5:7b"))
    assert await p.chat([{"role": "user", "content": "hi"}], json_mode=True) == '{"ok": true}'
    sent = json.loads(route.calls[0].request.content)
    assert sent["format"] == "json" and sent["model"] == "qwen2.5:7b" and sent["stream"] is False


@respx.mock
async def test_openai_compatible_provider_and_errors():
    respx.post("https://free.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "Hello"}}]})
    )
    p = OpenAICompatibleProvider(Settings(openai_base_url="https://free.test/v1", openai_api_key="k"))
    assert await p.chat([{"role": "user", "content": "hi"}]) == "Hello"
    respx.post("http://down.test/api/chat").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(LLMError):
        await OllamaProvider(Settings(ollama_url="http://down.test")).chat([{"role": "user", "content": "x"}])


def test_provider_factory():
    assert isinstance(get_provider(Settings(llm_provider="mock")), MockProvider)
    assert get_provider(Settings(llm_provider="ollama")).name.startswith("ollama:")
    assert get_provider(Settings(llm_provider="openai_compatible")).name.startswith("openai-compatible:")


async def test_mock_follow_up_uses_topic():
    out = await MockProvider().chat(
        [
            {"role": "system", "content": "[task:follow_up]"},
            {"role": "user", "content": '<data>\n{"topic": "finances"}\n</data>'},
        ]
    )
    assert "your finances" in out and out.endswith("?")


async def test_failed_job_retries_then_gives_up(monkeypatch):
    calls = {"n": 0}

    async def boom(db, payload):
        calls["n"] += 1
        raise RuntimeError("model crashed")

    monkeypatch.setitem(handlers.HANDLERS, "score", boom)
    async with dbmod.sessionmaker()() as db:
        queue.enqueue(db, "score", {"turn_id": 1})
        await db.commit()
    await queue.drain()
    async with dbmod.sessionmaker()() as db:
        job = await db.scalar(select(Job))
    assert calls["n"] == queue.MAX_ATTEMPTS and job.status == "failed" and "model crashed" in job.error


async def test_claims_are_exclusive_across_concurrent_workers(monkeypatch):
    seen: list[int] = []

    async def record(db, payload):
        seen.append(payload["i"])
        await asyncio.sleep(0.01)

    monkeypatch.setitem(handlers.HANDLERS, "score", record)
    async with dbmod.sessionmaker()() as db:
        for i in range(20):
            queue.enqueue(db, "score", {"i": i})
        await db.commit()

    async def worker():
        while await queue.run_one():
            pass

    if dbmod.engine().url.get_backend_name() == "postgresql":
        await asyncio.gather(*(worker() for _ in range(4)))  # real SKIP LOCKED contention
    else:
        await worker()  # SQLite has no row locks; run serially
    assert sorted(seen) == list(range(20))  # every job exactly once
