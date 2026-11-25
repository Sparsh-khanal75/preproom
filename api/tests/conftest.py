import os
import tempfile

# Configure BEFORE the app is imported (settings are cached)
_tmp = tempfile.mkdtemp(prefix="preproom-test-")
os.environ.setdefault("DATABASE_URL", os.getenv("TEST_DATABASE_URL", f"sqlite+aiosqlite:///{_tmp}/test.db"))
os.environ.update(
    ENV="test",
    RUN_JOBS_INLINE="true",
    LLM_PROVIDER="mock",
    STT_PROVIDER="mock",
    UPLOAD_DIR=f"{_tmp}/uploads",
    JWT_SECRET="test-secret-test-secret-test-secret-123",
)

import httpx  # noqa: E402
import pytest  # noqa: E402

from app import db as dbmod  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.packs.loader import sync_builtin_packs  # noqa: E402
from app.security import auth_limiter  # noqa: E402

VISA_PROFILE = {
    "country": "United Kingdom",
    "university": "University of Leeds",
    "course": "MSc Cyber Security",
    "city": "Leeds",
    "start_date": "September 2026",
    "modules": ["Network Security", "Digital Forensics"],
    "previous_study": "BE Computer Science, CGPA 8.18",
    "tuition_fee": "21500",
    "funding_source": "Father's savings and an education loan from Nabil Bank",
    "career_plan": "SOC analyst at a bank in Kathmandu",
}
GOOD = (
    "I chose the MSc Cyber Security at the University of Leeds because my final-year project was a SOC lab, "
    "and the Network Security module covers intrusion detection in depth. In September 2026 I start, and "
    "after graduating I plan to join a bank in Kathmandu as a SOC analyst, which is why this course fits."
)


@pytest.fixture(autouse=True)
async def database():
    dbmod.init_engine(os.environ["DATABASE_URL"])
    engine = dbmod.engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with dbmod.sessionmaker()() as s:
        await sync_builtin_packs(s)
    auth_limiter.hits.clear()
    yield
    await engine.dispose()


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def signup(c: httpx.AsyncClient, email: str, name: str = "Test User", password: str = "a-long-password") -> dict:
    r = await c.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


async def set_role(email: str, role: str) -> None:
    from sqlalchemy import update

    from app.models import User

    async with dbmod.sessionmaker()() as s:
        await s.execute(update(User).where(User.email == email).values(role=role))
        await s.commit()


@pytest.fixture
async def admin():
    async with client() as c:
        await signup(c, "admin@example.com", "Admin")  # first user becomes admin
        yield c


@pytest.fixture
async def candidate(admin):
    async with client() as c:
        await signup(c, "cand@example.com", "Candidate")
        yield c
