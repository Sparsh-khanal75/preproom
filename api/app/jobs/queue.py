"""A small, durable job queue on PostgreSQL.

Workers claim one job at a time with `SELECT ... FOR UPDATE SKIP LOCKED`, so several workers can run
in parallel without double-processing and without Redis. Failed jobs retry with backoff."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import sessionmaker
from ..models import Job

log = logging.getLogger("preproom.jobs")
MAX_ATTEMPTS = 3
MAX_WAIT = timedelta(minutes=15)


def enqueue(db: AsyncSession, kind: str, payload: dict, delay_s: float = 0) -> Job:
    job = Job(kind=kind, payload=payload, run_after=datetime.now(UTC) + timedelta(seconds=delay_s))
    db.add(job)
    return job


async def claim(db: AsyncSession) -> Job | None:
    stmt = (
        select(Job)
        .where(Job.status == "queued", Job.run_after <= datetime.now(UTC))
        .order_by(Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = await db.scalar(stmt)
    if job:
        job.status = "running"
        job.attempts += 1
        await db.commit()
    return job


class Retry(Exception):
    """Raise from a handler to re-run the job later without counting it as a failure."""

    def __init__(self, delay_s: float = 2.0):
        self.delay_s = delay_s


async def run_one() -> bool:
    """Claim and execute one job. Returns False when the queue is empty."""
    from .handlers import HANDLERS

    async with sessionmaker()() as db:
        job = await claim(db)
        if job is None:
            return False
        job_id, kind, payload = job.id, job.kind, dict(job.payload)
    try:
        async with sessionmaker()() as db:
            await HANDLERS[kind](db, payload)
            await db.commit()
        status, delay, error = "done", 0.0, None
    except Retry as r:
        status, delay, error = "retry", r.delay_s, None
    except Exception as e:  # noqa: BLE001 - recorded on the job row
        log.exception("job %s (%s) failed", job_id, kind)
        status, delay, error = "failed", 2.0**2, f"{type(e).__name__}: {e}"[:2000]
    now = datetime.now(UTC)
    async with sessionmaker()() as db:
        job = await db.get(Job, job_id)
        created = job.created_at if job.created_at.tzinfo else job.created_at.replace(tzinfo=UTC)
        if status == "done":
            job.status, job.finished_at = "done", now
        elif status == "retry" and now - created < MAX_WAIT:
            # waiting on other jobs is not a failure: don't consume an attempt
            job.status, job.attempts = "queued", max(job.attempts - 1, 0)
            job.run_after = now + timedelta(seconds=delay)
        elif status == "failed" and job.attempts < MAX_ATTEMPTS:
            job.status, job.error = "queued", error
            job.run_after = now + timedelta(seconds=delay * job.attempts)
        else:
            job.status, job.error, job.finished_at = "failed", error or "gave up waiting", now
        await db.commit()
    return True


async def drain(max_jobs: int = 200) -> None:
    """Run queued jobs in-process. Used by tests and the offline demo (RUN_JOBS_INLINE=true)."""
    for _ in range(max_jobs):
        async with sessionmaker()() as db:
            pending = await db.scalar(select(Job.id).where(Job.status == "queued").limit(1))
            if pending is None:
                return
            # make delayed jobs runnable immediately when draining inline
            due = await db.scalars(select(Job).where(Job.status == "queued"))
            for j in due:
                j.run_after = datetime.now(UTC)
            await db.commit()
        await run_one()


async def kick() -> None:
    if get_settings().run_jobs_inline:
        await drain()
