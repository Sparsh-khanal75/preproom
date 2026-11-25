import pytest

from app.speech import transcribe as tr

from .conftest import GOOD, VISA_PROFILE, client, set_role, signup

PACK = "student-visa-credibility"


async def ready(c):
    r = await c.put(f"/api/profiles/{PACK}", json={"data": VISA_PROFILE})
    assert r.json()["missing"] == []


async def run_interview(c, answer=GOOD) -> dict:
    s = (await c.post("/api/sessions", json={"pack": PACK})).json()
    for _ in range(30):
        if s["status"] != "active":
            break
        s = (await c.post(f"/api/sessions/{s['id']}/answer", json={"text": answer})).json()
    return s


async def test_profile_required_before_start(candidate):
    r = await candidate.post("/api/sessions", json={"pack": PACK})
    assert r.status_code == 422 and "University" in r.json()["detail"]["missing"]
    assert (await candidate.post("/api/sessions", json={"pack": "nope"})).status_code == 404


async def test_full_text_interview_produces_report(candidate):
    await ready(candidate)
    s = await run_interview(candidate)
    assert s["status"] == "done", s["status"]
    rep = s["report"]
    assert 0 <= rep["overall"] <= 100 and rep["answered"] == len(s["turns"])
    assert set(rep["subscores"]) == {"consistency", "specificity", "relevance", "language"}  # no fluency for text
    assert rep["judge"] == "mock" and "Practice estimate" in rep["disclaimer"]
    assert len(s["turns"]) == s["planned_questions"]  # good answers trigger no follow-ups
    assert all(t["status"] == "scored" and t["scores"]["evidence"] for t in s["turns"])
    # questions are personalised from the profile
    assert any("MSc Cyber Security" in t["question_text"] for t in s["turns"])


async def test_short_answer_gets_exactly_one_follow_up(candidate):
    await ready(candidate)
    s = (await candidate.post("/api/sessions", json={"pack": PACK})).json()
    first = s["turns"][0]["question_id"]
    s = (await candidate.post(f"/api/sessions/{s['id']}/answer", json={"text": "Because it is good."})).json()
    assert s["turns"][-1]["is_follow_up"] and s["turns"][-1]["question_id"] == first
    s = (await candidate.post(f"/api/sessions/{s['id']}/answer", json={"text": "It is nice."})).json()
    assert not s["turns"][-1]["is_follow_up"] and s["turns"][-1]["question_id"] != first


async def test_answer_state_rules(candidate):
    await ready(candidate)
    s = await run_interview(candidate)
    r = await candidate.post(f"/api/sessions/{s['id']}/answer", json={"text": "late"})
    assert r.status_code == 409
    assert (await candidate.post(f"/api/sessions/{s['id']}/answer", json={"text": ""})).status_code == 422


async def test_finish_early_drops_unanswered_question(candidate):
    await ready(candidate)
    s = (await candidate.post("/api/sessions", json={"pack": PACK})).json()
    s = (await candidate.post(f"/api/sessions/{s['id']}/answer", json={"text": GOOD})).json()
    s = (await candidate.post(f"/api/sessions/{s['id']}/finish")).json()
    assert s["status"] == "done" and len(s["turns"]) == 1 and s["report"]["answered"] == 1


async def test_voice_answer_is_transcribed_and_measured(candidate, monkeypatch):
    spoken = "Um, I chose the MSc Cyber Security at the University of Leeds. " + GOOD

    class Fake:
        async def transcribe(self, path):
            words, t = [], 0.0
            for w in spoken.split():
                words.append({"w": w, "start": t, "end": t + 0.3})
                t += 0.45
            return tr.Transcript(spoken, words, t, "fake")

    monkeypatch.setattr("app.jobs.handlers.get_transcriber", lambda: Fake())
    await ready(candidate)
    s = (await candidate.post("/api/sessions", json={"pack": PACK})).json()
    r = await candidate.post(
        f"/api/sessions/{s['id']}/answer-audio",
        files={"audio": ("a.webm", b"\x1a\x45\xdf\xa3" + b"0" * 2000, "audio/webm")},
    )
    assert r.status_code == 202
    s = (await candidate.get(f"/api/sessions/{s['id']}")).json()
    t0 = s["turns"][0]
    assert t0["answer_mode"] == "voice" and t0["has_audio"] and t0["answer_text"] == spoken
    assert t0["metrics"]["fillers"]["um"] == 1 and 120 < t0["metrics"]["words_per_minute"] < 140
    assert t0["scores"]["subscores"]["fluency"] is not None
    audio = await candidate.get(f"/api/turns/{t0['id']}/audio")
    assert audio.status_code == 200 and audio.content.startswith(b"\x1a\x45")


async def test_audio_upload_validation(candidate, monkeypatch):
    await ready(candidate)
    s = (await candidate.post("/api/sessions", json={"pack": PACK})).json()
    bad_type = await candidate.post(
        f"/api/sessions/{s['id']}/answer-audio", files={"audio": ("x.exe", b"MZ", "application/x-msdownload")}
    )
    assert bad_type.status_code == 415
    monkeypatch.setattr(
        "app.routers.sessions.get_settings",
        lambda: type("S", (), {"max_audio_bytes": 10, "upload_dir": "/tmp/pr-up"})(),
    )
    big = await candidate.post(f"/api/sessions/{s['id']}/answer-audio", files={"audio": ("a.webm", b"0" * 100, "audio/webm")})
    assert big.status_code == 413


async def test_other_users_cannot_see_or_answer(candidate):
    await ready(candidate)
    s = await run_interview(candidate)
    async with client() as other:
        await signup(other, "other@example.com")
        assert (await other.get(f"/api/sessions/{s['id']}")).status_code == 404
        assert (await other.post(f"/api/sessions/{s['id']}/answer", json={"text": "x"})).status_code == 404
        assert (await other.get(f"/api/turns/{s['turns'][0]['id']}/comments")).status_code == 404


async def test_coach_access_is_granted_and_revoked_by_candidate(candidate):
    await ready(candidate)
    s = await run_interview(candidate)
    async with client() as coach:
        await signup(coach, "coach@example.com", "Coach")
        await set_role("coach@example.com", "coach")
        assert (await coach.get(f"/api/sessions/{s['id']}")).status_code == 404  # no consent yet
        assert (await candidate.post("/api/coach-access", json={"coach_email": "nobody@example.com"})).status_code == 404
        granted = await candidate.post("/api/coach-access", json={"coach_email": "coach@example.com"})
        assert granted.status_code == 201
        assert (await coach.get(f"/api/sessions/{s['id']}")).status_code == 200
        cands = (await coach.get("/api/coach/candidates")).json()
        assert cands[0]["email"] == "cand@example.com" and cands[0]["last_score"] == s["overall_score"]
        prog = await coach.get(f"/api/coach/candidates/{cands[0]['id']}/progress")
        assert prog.json()["totals"]["sessions_done"] == 1
        tid = s["turns"][0]["id"]
        c = await coach.post(f"/api/turns/{tid}/comments", json={"body": "Name the module earlier."})
        assert c.status_code == 201
        comments = (await candidate.get(f"/api/turns/{tid}/comments")).json()
        assert comments[0]["author_role"] == "coach"
        await candidate.delete(f"/api/coach-access/{granted.json()['id']}")
        assert (await coach.get(f"/api/sessions/{s['id']}")).status_code == 404
        assert (await candidate.get("/api/coach/candidates")).status_code == 403


async def test_progress_trend(candidate):
    await ready(candidate)
    await run_interview(candidate, answer="Because it is good and I like it a lot, honestly, it is the best choice.")
    await run_interview(candidate)
    p = (await candidate.get("/api/progress")).json()
    assert p["totals"]["sessions_done"] == 2 and len(p["trend"]) == 2
    assert p["totals"]["improvement"] > 0  # the detailed answers scored higher
    assert set(p["weakest"]) <= {"consistency", "specificity", "relevance", "language"}


async def test_delete_session(candidate):
    await ready(candidate)
    s = await run_interview(candidate)
    assert (await candidate.delete(f"/api/sessions/{s['id']}")).status_code == 204
    assert (await candidate.get(f"/api/sessions/{s['id']}")).status_code == 404


async def test_admin_user_management(admin, candidate):
    users = (await admin.get("/api/admin/users")).json()
    cand = next(u for u in users if u["email"] == "cand@example.com")
    r = await admin.patch(f"/api/admin/users/{cand['id']}/role", json={"role": "coach"})
    assert r.json()["role"] == "coach"
    me = next(u for u in users if u["email"] == "admin@example.com")
    assert (await admin.patch(f"/api/admin/users/{me['id']}/role", json={"role": "candidate"})).status_code == 409
    assert (await candidate.get("/api/admin/users")).status_code == 403


@pytest.mark.parametrize("pack", ["university-admission", "job-behavioral", "tech-concepts"])
async def test_every_builtin_pack_runs_end_to_end(candidate, pack):
    detail = (await candidate.get(f"/api/packs/{pack}")).json()
    data = {f["id"]: (["Python", "SQL"] if f["type"] == "list" else "Example Value Corp") for f in detail["profile_fields"]}
    await candidate.put(f"/api/profiles/{pack}", json={"data": data})
    s = (await candidate.post("/api/sessions", json={"pack": pack})).json()
    for _ in range(40):
        if s["status"] != "active":
            break
        s = (await candidate.post(f"/api/sessions/{s['id']}/answer", json={"text": GOOD})).json()
    assert s["status"] == "done" and s["report"]["overall"] is not None
