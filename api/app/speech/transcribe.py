"""Speech-to-text. faster-whisper runs locally on CPU for free; the mock is for tests and demos."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..config import Settings, get_settings


@dataclass
class Transcript:
    text: str
    words: list[dict] = field(default_factory=list)  # [{"w": str, "start": float, "end": float}]
    duration: float = 0.0
    engine: str = ""


class Transcriber(Protocol):
    async def transcribe(self, path: str) -> Transcript: ...


class WhisperTranscriber:
    _models: dict[str, object] = {}

    def __init__(self, model: str):
        self.model_name = model

    def _model(self):
        if self.model_name not in self._models:
            from faster_whisper import WhisperModel  # heavy import, loaded on first use

            self._models[self.model_name] = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        return self._models[self.model_name]

    def _run(self, path: str) -> Transcript:
        segments, info = self._model().transcribe(path, word_timestamps=True, vad_filter=True, language="en")
        words, text = [], []
        for seg in segments:
            text.append(seg.text.strip())
            for w in seg.words or []:
                words.append({"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})
        return Transcript(" ".join(text).strip(), words, round(info.duration, 2), f"whisper:{self.model_name}")

    async def transcribe(self, path: str) -> Transcript:
        return await asyncio.to_thread(self._run, path)


class MockTranscriber:
    """Reads `<audio>.txt` if present (tests, demo fixtures), and fakes word timings at ~2.3 words/s
    with one 2.5 s pause after the first sentence, so fluency metrics have something to measure."""

    @staticmethod
    def _read_sidecar(path: str) -> str:
        sidecar = Path(path + ".txt")
        if sidecar.exists():
            return sidecar.read_text(encoding="utf-8").strip()
        return "This is a mock transcript. Set STT_PROVIDER=whisper for real speech-to-text."

    async def transcribe(self, path: str) -> Transcript:
        text = await asyncio.to_thread(self._read_sidecar, path)
        words, t = [], 0.0
        first_sentence_end = len(re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0].split())
        for i, w in enumerate(text.split()):
            words.append({"w": w, "start": round(t, 2), "end": round(t + 0.35, 2)})
            t += 0.43
            if i + 1 == first_sentence_end:
                t += 2.5
        return Transcript(text, words, round(t, 2), "mock")


def get_transcriber(s: Settings | None = None) -> Transcriber:
    s = s or get_settings()
    return WhisperTranscriber(s.whisper_model) if s.stt_provider == "whisper" else MockTranscriber()
