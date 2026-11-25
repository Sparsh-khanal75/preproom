"""Progress dashboard, coach access (granted by the candidate), and admin user management."""

from __future__ import annotations

from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Assignment, InterviewSession, User
from ..packs.loader import get_pack
from ..schemas import CandidateOut, CoachAccessIn, ProgressOut, RoleIn, SessionSummary, UserOut
from ..security import can_view_candidate, current_user, require_role

router = APIRouter(prefix="/api", tags=["people"])
SUB = ("consistency", "specificity", "relevance", "fluency", "language")


async def progress_for(db: AsyncSession, user_id: int) -> ProgressOut:
    rows = (
        await db.scalars(
            select(InterviewSession)
            .where(InterviewSession.user_id == user_id)
            .options(selectinload(InterviewSession.turns))
            .order_by(InterviewSession.started_at)
        )
    ).all()
    sessions, trend = [], []
    sub_vals: dict[str, list[float]] = {k: [] for k in SUB}
    fillers, wpm = 0, []
    for s in rows:
        pack = await get_pack(db, s.pack_slug)
        name = pack.name if pack else s.pack_slug
        sessions.append(
            SessionSummary(
                id=s.id,
                pack_slug=s.pack_slug,
                pack_name=name,
                status=s.status,
                overall_score=s.overall_score,
                started_at=s.started_at,
                answered=sum(1 for t in s.turns if t.answer_text),
            )
        )
        if s.status == "done" and s.report and s.report.get("overall") is not None:
            point = {"session_id": s.id, "date": s.started_at.isoformat(), "pack": name, "overall": s.overall_score}
            point.update(s.report.get("subscores", {}))
            trend.append(point)
            for k, v in s.report.get("subscores", {}).items():
                sub_vals[k].append(v)
            if s.report.get("delivery"):
                fillers += s.report["delivery"]["filler_total"]
                wpm.append(s.report["delivery"]["avg_words_per_minute"])
    averages = {k: round(mean(v), 1) for k, v in sub_vals.items() if v}
    weakest = [k for k, _ in sorted(averages.items(), key=lambda kv: kv[1])[:2]]
    done = [p["overall"] for p in trend]
    totals = {
        "sessions_done": len(done),
        "best": max(done) if done else None,
        "latest": done[-1] if done else None,
        "improvement": (done[-1] - done[0]) if len(done) >= 2 else None,
        "filler_words": fillers,
        "avg_wpm": round(mean(wpm)) if wpm else None,
    }
    sessions.reverse()
    return ProgressOut(sessions=sessions, trend=trend, subscore_averages=averages, weakest=weakest, totals=totals)


@router.get("/progress", response_model=ProgressOut)
async def my_progress(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    return await progress_for(db, user.id)


# --- coach access: the CANDIDATE grants it (consent), and can revoke it -----------------------
@router.get("/coach-access", response_model=list[UserOut])
async def my_coaches(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        await db.scalars(select(User).join(Assignment, Assignment.coach_id == User.id).where(Assignment.candidate_id == user.id))
    ).all()
    return [UserOut(id=u.id, email=u.email, name=u.name, role=u.role) for u in rows]


@router.post("/coach-access", response_model=UserOut, status_code=201)
async def grant_coach(body: CoachAccessIn, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    coach = await db.scalar(select(User).where(func.lower(User.email) == body.coach_email.lower()))
    if not coach or coach.role != "coach":
        raise HTTPException(404, "No coach account with that email")
    exists = await db.scalar(select(Assignment.id).where(Assignment.coach_id == coach.id, Assignment.candidate_id == user.id))
    if not exists:
        db.add(Assignment(coach_id=coach.id, candidate_id=user.id))
        await db.commit()
    return UserOut(id=coach.id, email=coach.email, name=coach.name, role=coach.role)


@router.delete("/coach-access/{coach_id}", status_code=204)
async def revoke_coach(coach_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    a = await db.scalar(select(Assignment).where(Assignment.coach_id == coach_id, Assignment.candidate_id == user.id))
    if a:
        await db.delete(a)
        await db.commit()


@router.get("/coach/candidates", response_model=list[CandidateOut])
async def coach_candidates(db: AsyncSession = Depends(get_db), coach: User = Depends(require_role("coach", "admin"))):
    q = select(User).join(Assignment, Assignment.candidate_id == User.id).where(Assignment.coach_id == coach.id)
    out = []
    for u in (await db.scalars(q)).all():
        scores = (
            await db.scalars(
                select(InterviewSession.overall_score)
                .where(InterviewSession.user_id == u.id, InterviewSession.status == "done")
                .order_by(InterviewSession.started_at)
            )
        ).all()
        scores = [x for x in scores if x is not None]
        n = await db.scalar(select(func.count(InterviewSession.id)).where(InterviewSession.user_id == u.id))
        out.append(
            CandidateOut(
                id=u.id,
                name=u.name,
                email=u.email,
                sessions=n or 0,
                last_score=scores[-1] if scores else None,
                average_score=round(mean(scores), 1) if scores else None,
            )
        )
    return out


@router.get("/coach/candidates/{candidate_id}/progress", response_model=ProgressOut)
async def candidate_progress(
    candidate_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_role("coach", "admin"))
):
    if not await can_view_candidate(db, user, candidate_id):
        raise HTTPException(404, "Candidate not found")
    return await progress_for(db, candidate_id)


# --- admin ------------------------------------------------------------------------------------
@router.get("/admin/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), _: User = Depends(require_role("admin"))):
    rows = (await db.scalars(select(User).order_by(User.created_at))).all()
    return [UserOut(id=u.id, email=u.email, name=u.name, role=u.role) for u in rows]


@router.patch("/admin/users/{user_id}/role", response_model=UserOut)
async def set_role(user_id: int, body: RoleIn, db: AsyncSession = Depends(get_db), admin: User = Depends(require_role("admin"))):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and body.role != "admin":
        raise HTTPException(409, "You can't remove your own admin role")
    u.role = body.role
    await db.commit()
    return UserOut(id=u.id, email=u.email, name=u.name, role=u.role)
