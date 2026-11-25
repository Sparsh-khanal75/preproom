"""Background job handlers: transcribe a recorded answer, score an answer, build a session report."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..interview import engine
from ..llm.providers import get_provider
from ..models import InterviewSession, Turn
from ..packs.loader import get_pack
from ..scoring.judge import judge
from ..scoring.report import build_report
from ..scoring.score import relevant_profile, score_answer
from ..speech.metrics import speech_metrics
from ..speech.transcribe import get_transcriber
from .queue import Retry


async def _session(db: AsyncSession, session_id: int) -> InterviewSession:
    return await db.scalar(
        select(InterviewSession).where(InterviewSession.id == session_id).options(selectinload(InterviewSession.turns))
    )


async def transcribe(db: AsyncSession, payload: dict) -> None:
    turn = await db.get(Turn, payload["turn_id"])
    if turn is None or turn.status != "transcribing":
        return
    s = await _session(db, turn.session_id)
    pack = await get_pack(db, s.pack_slug)
    tr = await get_transcriber().transcribe(turn.audio_path)
    text = tr.text or "(no speech detected)"
    metrics = speech_metrics(text, tr.words, tr.duration)
    metrics["stt_engine"] = tr.engine
    turn = next(t for t in s.turns if t.id == payload["turn_id"])
    await engine.record_answer(db, s, pack, turn, text, "voice", tr.words, metrics)


async def score(db: AsyncSession, payload: dict) -> None:
    turn = await db.get(Turn, payload["turn_id"])
    if turn is None or not turn.answer_text:
        return
    s = await db.get(InterviewSession, turn.session_id)
    pack = await get_pack(db, s.pack_slug)
    q = engine.question(pack, turn.question_id)
    profile = s.profile_snapshot
    metrics = turn.metrics or speech_metrics(turn.answer_text, None, None)
    verdict, note = await judge(get_provider(), turn.question_text, turn.answer_text, relevant_profile(profile, q))
    turn.scores = score_answer(pack, q, profile, turn.answer_text, metrics, verdict, note)
    turn.metrics = metrics
    turn.status = "scored"


async def report(db: AsyncSession, payload: dict) -> None:
    s = await _session(db, payload["session_id"])
    if s is None or s.status == "done":
        return
    if any(t.status in ("answered", "transcribing") for t in s.turns):
        raise Retry(2.0)  # wait for outstanding transcriptions and scores
    pack = await get_pack(db, s.pack_slug)
    s.report = build_report(s, pack, get_provider().name)
    s.overall_score = s.report["overall"]
    s.status = "done"


HANDLERS = {"transcribe": transcribe, "score": score, "report": report}
