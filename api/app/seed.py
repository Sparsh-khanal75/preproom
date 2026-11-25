"""Demo data: `python -m app.seed`. Creates three demo accounts and two scored practice interviews.

Only runs on an empty database. The demo password comes from DEMO_PASSWORD (dev use only)."""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import func, select

from .db import sessionmaker
from .interview import engine
from .jobs.queue import drain
from .models import Assignment, InterviewSession, Profile, User
from .packs.loader import get_pack, sync_builtin_packs
from .security import hash_password

PACK = "student-visa-credibility"
PROFILE = {
    "country": "United Kingdom",
    "university": "University of Leeds",
    "course": "MSc Cyber Security",
    "city": "Leeds",
    "start_date": "September 2026",
    "modules": ["Network Security", "Digital Forensics"],
    "previous_study": "BE Computer Science, first class",
    "tuition_fee": 21500,
    "funding_source": "My father's savings plus an education loan from a bank in Kathmandu",
    "career_plan": "SOC analyst at a bank in Kathmandu, then incident response lead",
    "home_ties": "Parents and younger sister in Kathmandu; job offer pathway with my previous employer",
}
WEAK = {
    "why-course": "Because it is a good course and I like computers.",
    "why-university": "I have always been passionate about this field since my childhood and the university is one of the best "
    "universities in the world with world-class facilities and a multicultural environment.",
    "funding": "My parents will pay the 25,000 pounds fee, they have enough money.",
    "career-plan": "I will get a good job in a reputed company after my studies.",
    "*": "I am not sure, I think it is fine.",
}
STRONG = {
    "why-course": "I chose the MSc Cyber Security because my final-year project was a detection lab built on Sysmon logs, "
    "and the Network Security module goes deeper into intrusion detection, which is exactly what a SOC analyst needs.",
    "why-university": "I compared the University of Leeds with two other universities. Leeds teaches Digital Forensics with a "
    "hands-on lab, its fee of 21,500 pounds fit our budget, and Nepal has no equivalent master's with that module.",
    "modules": "Network Security covers intrusion detection and firewall design, and Digital Forensics teaches evidence "
    "handling and disk analysis. Both map directly to the SOC analyst role I am aiming for in Kathmandu.",
    "funding": "The tuition fee is 21,500 pounds. My father is paying 12,000 from his savings and the rest comes from an "
    "education loan from a bank in Kathmandu, which also covers about 1,100 pounds a month for living costs in Leeds.",
    "career-plan": "After graduating in 2027 I plan to return to Kathmandu as a SOC analyst at a bank, because banks there "
    "are building security teams, and in about five years I want to lead incident response.",
    "start-date": "The course starts in September 2026 and runs for twelve months, with a dissertation in the summer term.",
    "previous-study": "My bachelor's was BE Computer Science, where I took networking and cryptography, so this master's is "
    "a direct progression rather than a change of field.",
    "city-living": "Leeds is a student city; I have booked university accommodation at about 650 pounds a month and will "
    "walk to campus.",
    "home-ties": "My parents and younger sister live in Kathmandu, and my previous employer has said they would rehire me "
    "as a security analyst when I return in 2027.",
    "gaps": "I had a six-month gap in 2025 when I completed the TryHackMe SOC Level 1 path and did a security internship.",
    "alternatives": "I also applied to two other UK universities. I chose the University of Leeds because of the Digital "
    "Forensics lab and the lower fee of 21,500 pounds.",
    "research": "I read the module handbook on the Leeds website, joined an online open day in March 2026, and spoke to a "
    "Nepali alumnus who now works in a SOC in London.",
    "*": "I researched this carefully and can give specific details from my plan.",
}


async def _interview(db, user: User, answers: dict[str, str]) -> None:
    pack = await get_pack(db, PACK)
    s = await engine.start(db, user.id, pack, PROFILE, seed=user.id)
    await db.commit()
    while True:
        s = await db.scalar(select(InterviewSession).where(InterviewSession.id == s.id).execution_options(populate_existing=True))
        await db.refresh(s, ["turns"])
        if s.status != "active":
            break
        turn = s.turns[-1]
        await engine.record_answer(db, s, pack, turn, answers.get(turn.question_id, answers["*"]), "text")
        await db.commit()
    await drain()


async def main() -> None:
    password = os.getenv("DEMO_PASSWORD", "preproom-demo-2026")
    async with sessionmaker()() as db:
        await sync_builtin_packs(db)
        if await db.scalar(select(func.count(User.id))):
            print("Database already has users - seed skipped.")
            return
        admin = User(email="admin@preproom.dev", name="Demo Admin", role="admin", password_hash=hash_password(password))
        coach = User(email="coach@preproom.dev", name="Demo Coach", role="coach", password_hash=hash_password(password))
        cand = User(
            email="candidate@preproom.dev", name="Demo Candidate", role="candidate", password_hash=hash_password(password)
        )
        db.add_all([admin, coach, cand])
        await db.flush()
        db.add(Profile(user_id=cand.id, pack_slug=PACK, data=PROFILE))
        db.add(Assignment(coach_id=coach.id, candidate_id=cand.id))
        await db.commit()
        await _interview(db, cand, WEAK)
        await _interview(db, cand, STRONG)
    print(f"Seeded demo accounts (password: {password}): candidate@preproom.dev, coach@preproom.dev, admin@preproom.dev")


if __name__ == "__main__":
    asyncio.run(main())
