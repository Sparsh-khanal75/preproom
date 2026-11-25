from __future__ import annotations

import asyncio
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..db import get_db
from ..interview import engine
from ..jobs.queue import enqueue, kick
from ..models import Comment, InterviewSession, Profile, Turn, User
from ..packs.loader import get_pack
from ..schemas import AnswerText, CommentIn, CommentOut, SessionOut, SessionSummary, StartSession, TurnOut
from ..security import can_view_candidate, current_user

router = APIRouter(prefix="/api", tags=["sessions"])
AUDIO_TYPES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
}


async def load(db: AsyncSession, session_id: int) -> InterviewSession | None:
    return await db.scalar(
        select(InterviewSession)
        .where(InterviewSession.id == session_id)
        .options(selectinload(InterviewSession.turns))
        .execution_options(populate_existing=True)
    )


async def visible(db: AsyncSession, session_id: int, user: User) -> InterviewSession:
    s = await load(db, session_id)
    if not s or not await can_view_candidate(db, user, s.user_id):
        raise HTTPException(404, "Session not found")  # 404, not 403: don't reveal that it exists
    return s


async def owned(db: AsyncSession, session_id: int, user: User) -> InterviewSession:
    s = await load(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Session not found")
    return s


def turn_out(t: Turn) -> TurnOut:
    return TurnOut(
        id=t.id,
        index=t.index,
        question_id=t.question_id,
        question_text=t.question_text,
        is_follow_up=t.is_follow_up,
        answer_text=t.answer_text,
        answer_mode=t.answer_mode,
        has_audio=bool(t.audio_path),
        status=t.status,
        metrics=t.metrics,
        scores=t.scores,
    )


async def session_out(db: AsyncSession, s: InterviewSession) -> SessionOut:
    pack = await get_pack(db, s.pack_slug)
    return SessionOut(
        id=s.id,
        user_id=s.user_id,
        pack_slug=s.pack_slug,
        pack_name=pack.name if pack else s.pack_slug,
        status=s.status,
        overall_score=s.overall_score,
        started_at=s.started_at,
        finished_at=s.finished_at,
        planned_questions=len(s.plan),
        turns=[turn_out(t) for t in s.turns],
        report=s.report,
    )


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def start_session(body: StartSession, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    pack = await get_pack(db, body.pack)
    if not pack:
        raise HTTPException(404, "Interview type not found")
    prof = await db.scalar(select(Profile).where(Profile.user_id == user.id, Profile.pack_slug == pack.id))
    count = await db.scalar(select(func.count(InterviewSession.id)).where(InterviewSession.user_id == user.id))
    try:
        s = await engine.start(db, user.id, pack, prof.data if prof else {}, seed=user.id * 1000 + (count or 0))
    except engine.ProfileIncomplete as e:
        raise HTTPException(422, {"message": "Complete your profile first", "missing": e.missing}) from e
    await db.commit()
    return await session_out(db, await load(db, s.id))


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        await db.scalars(
            select(InterviewSession)
            .where(InterviewSession.user_id == user.id)
            .options(selectinload(InterviewSession.turns))
            .order_by(InterviewSession.started_at.desc())
        )
    ).all()
    out = []
    for s in rows:
        pack = await get_pack(db, s.pack_slug)
        out.append(
            SessionSummary(
                id=s.id,
                pack_slug=s.pack_slug,
                pack_name=pack.name if pack else s.pack_slug,
                status=s.status,
                overall_score=s.overall_score,
                started_at=s.started_at,
                answered=sum(1 for t in s.turns if t.answer_text),
            )
        )
    return out


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    return await session_out(db, await visible(db, session_id, user))


def _awaiting(s: InterviewSession) -> Turn:
    if s.status != "active":
        raise HTTPException(409, f"Session is {s.status}; it is not waiting for an answer")
    turn = engine.current_turn(s)
    if turn.status != "asked":
        raise HTTPException(409, "This question was already answered")
    return turn


@router.post("/sessions/{session_id}/answer", response_model=SessionOut)
async def answer_text(session_id: int, body: AnswerText, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    s = await owned(db, session_id, user)
    turn = _awaiting(s)
    pack = await get_pack(db, s.pack_slug)
    await engine.record_answer(db, s, pack, turn, body.text.strip(), "text")
    await db.commit()
    await kick()
    return await session_out(db, await load(db, session_id))


@router.post("/sessions/{session_id}/answer-audio", response_model=SessionOut, status_code=202)
async def answer_audio(
    session_id: int,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    s = await owned(db, session_id, user)
    turn = _awaiting(s)
    ctype = (audio.content_type or "").split(";")[0].strip()
    if ctype not in AUDIO_TYPES:
        raise HTTPException(415, f"Unsupported audio type {ctype!r}")
    limit = get_settings().max_audio_bytes
    folder = Path(get_settings().upload_dir) / str(s.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{turn.id}-{secrets.token_hex(8)}{AUDIO_TYPES[ctype]}"  # server-chosen name only
    size = 0
    with path.open("wb") as fh:
        while chunk := await audio.read(64 * 1024):
            size += len(chunk)
            if size > limit:
                fh.close()
                path.unlink(missing_ok=True)
                raise HTTPException(413, "Recording is too large (max 10 MB)")
            fh.write(chunk)
    turn.audio_path, turn.status, turn.answer_mode = str(path), "transcribing", "voice"
    s.status = "processing"
    enqueue(db, "transcribe", {"turn_id": turn.id})
    await db.commit()
    await kick()
    return await session_out(db, await load(db, session_id))


@router.post("/sessions/{session_id}/finish", response_model=SessionOut)
async def finish_early(session_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    s = await owned(db, session_id, user)
    if s.status not in ("active", "processing"):
        raise HTTPException(409, f"Session is already {s.status}")
    last = engine.current_turn(s)
    if last.status == "asked":
        await db.delete(last)  # unanswered question is not part of the result
    await engine.finish(db, s)
    await db.commit()
    await kick()
    return await session_out(db, await load(db, session_id))


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    s = await owned(db, session_id, user)
    for t in s.turns:
        if t.audio_path:
            await asyncio.to_thread(Path(t.audio_path).unlink, missing_ok=True)
    await db.delete(s)
    await db.commit()


@router.get("/turns/{turn_id}/audio")
async def turn_audio(turn_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    t = await db.get(Turn, turn_id)
    s = await db.get(InterviewSession, t.session_id) if t else None
    if not t or not t.audio_path or not s or not await can_view_candidate(db, user, s.user_id):
        raise HTTPException(404, "Recording not found")
    return FileResponse(t.audio_path)


@router.get("/turns/{turn_id}/comments", response_model=list[CommentOut])
async def list_comments(turn_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    t = await db.get(Turn, turn_id)
    s = await db.get(InterviewSession, t.session_id) if t else None
    if not s or not await can_view_candidate(db, user, s.user_id):
        raise HTTPException(404, "Answer not found")
    rows = (
        await db.execute(
            select(Comment, User)
            .join(User, User.id == Comment.author_id)
            .where(Comment.turn_id == turn_id)
            .order_by(Comment.created_at)
        )
    ).all()
    return [
        CommentOut(id=c.id, turn_id=c.turn_id, author_name=u.name, author_role=u.role, body=c.body, created_at=c.created_at)
        for c, u in rows
    ]


@router.post("/turns/{turn_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(turn_id: int, body: CommentIn, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    t = await db.get(Turn, turn_id)
    s = await db.get(InterviewSession, t.session_id) if t else None
    if not s or not await can_view_candidate(db, user, s.user_id):
        raise HTTPException(404, "Answer not found")
    c = Comment(turn_id=turn_id, author_id=user.id, body=body.body.strip())
    db.add(c)
    await db.commit()
    return CommentOut(
        id=c.id, turn_id=turn_id, author_name=user.name, author_role=user.role, body=c.body, created_at=c.created_at
    )
