import pytest

from app.packs.loader import PackError, builtin_files, parse_pack

from .conftest import client, signup

MINIMAL_PACK = """
id: custom-sales
name: Sales role
description: Practise a sales interview
persona: A sales director.
session_length: 3
profile_fields:
  - {id: company, label: Company, entity: true}
questions:
  - {id: q1, text: "Why {company}?", topic: motivation}
  - {id: q2, text: Sell me this pen., topic: pitch}
  - {id: q3, text: Tell me about a deal you closed., topic: results}
rubric: {specificity: 0.4, relevance: 0.4, language: 0.2}
"""


async def test_first_user_is_admin_then_candidates():
    async with client() as c:
        assert (await signup(c, "a@example.com"))["role"] == "admin"
        assert (await signup(c, "b@example.com"))["role"] == "candidate"
        r = await c.post("/api/auth/register", json={"email": "B@example.com", "name": "x", "password": "a-long-password"})
        assert r.status_code == 409


async def test_login_logout_and_me():
    async with client() as c:
        await signup(c, "a@example.com")
        assert (await c.get("/api/auth/me")).status_code == 200
        await c.post("/api/auth/logout")
        assert (await c.get("/api/auth/me")).status_code == 401
        bad = await c.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
        assert bad.status_code == 401
        unknown = await c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
        assert unknown.status_code == 401 and unknown.json() == bad.json()  # no user enumeration
        ok = await c.post("/api/auth/login", json={"email": "A@example.com", "password": "a-long-password"})
        assert ok.status_code == 200 and "httponly" in ok.headers["set-cookie"].lower()


async def test_weak_password_and_rate_limit():
    async with client() as c:
        r = await c.post("/api/auth/register", json={"email": "a@example.com", "name": "x", "password": "short"})
        assert r.status_code == 422
        codes = [
            (await c.post("/api/auth/login", json={"email": "z@example.com", "password": "x"})).status_code for _ in range(12)
        ]
        assert codes[-1] == 429


async def test_security_headers():
    async with client() as c:
        r = await c.get("/api/health")
        assert r.json()["llm"] == "mock"
        assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"


def test_builtin_packs_are_valid():
    ids = [parse_pack(p.read_text()).id for p in builtin_files()]
    assert {"student-visa-credibility", "university-admission", "job-behavioral", "tech-concepts"} <= set(ids)


@pytest.mark.parametrize(
    "bad, msg",
    [
        ("id: x", "should match pattern"),
        (MINIMAL_PACK.replace("0.2}", "0.5}"), "must sum to 1.0"),
        (MINIMAL_PACK.replace("Why {company}?", "Why {employer}?"), "unknown profile fields"),
        ("!!python/object/apply:os.system ['echo hacked']", "invalid YAML"),
        ("- just\n- a list", "must be a YAML mapping"),
    ],
)
def test_invalid_packs_are_rejected(bad, msg):
    with pytest.raises(PackError, match=msg):
        parse_pack(bad)


async def test_pack_upload_is_admin_only(admin, candidate):
    assert (await candidate.post("/api/packs", json={"yaml": MINIMAL_PACK})).status_code == 403
    r = await admin.post("/api/packs", json={"yaml": MINIMAL_PACK})
    assert r.status_code == 201 and r.json()["slug"] == "custom-sales"
    slugs = [p["slug"] for p in (await candidate.get("/api/packs")).json()]
    assert "custom-sales" in slugs
    bad = await admin.post("/api/packs", json={"yaml": "id: x"})
    assert bad.status_code == 422
    builtin = await admin.post("/api/packs", json={"yaml": MINIMAL_PACK.replace("custom-sales", "job-behavioral")})
    assert builtin.status_code == 409
    off = await admin.patch("/api/packs/custom-sales/active", params={"active": False})
    assert off.json()["active"] is False
    assert "custom-sales" not in [p["slug"] for p in (await candidate.get("/api/packs")).json()]


async def test_profile_validation(candidate):
    detail = (await candidate.get("/api/packs/student-visa-credibility")).json()
    assert any(f["id"] == "tuition_fee" and f["type"] == "number" for f in detail["profile_fields"])
    r = await candidate.put("/api/profiles/student-visa-credibility", json={"data": {"tuition_fee": "lots"}})
    assert r.status_code == 422
    r = await candidate.put(
        "/api/profiles/student-visa-credibility",
        json={"data": {"tuition_fee": "21,500", "modules": "A\nB\n", "unknown": "dropped"}},
    )
    body = r.json()
    assert body["data"] == {"tuition_fee": 21500, "modules": ["A", "B"]}
    assert "University" in body["missing"]
