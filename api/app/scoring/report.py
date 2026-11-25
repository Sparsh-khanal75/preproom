"""Session report: aggregate per-answer scores into an overall score, strengths, fixes and flags."""

from __future__ import annotations

from statistics import mean

from ..models import InterviewSession
from ..packs.schema import SUBSCORES, Pack

LABEL = {
    "consistency": "Consistency",
    "specificity": "Specificity",
    "relevance": "Relevance",
    "fluency": "Fluency",
    "language": "Language",
}


def build_report(s: InterviewSession, pack: Pack, judge_name: str) -> dict:
    scored = [t for t in s.turns if t.scores]
    if not scored:
        return {"overall": None, "summary": "No answers were recorded.", "per_question": []}
    sub_avg = {}
    for k in SUBSCORES:
        vals = [t.scores["subscores"][k] for t in scored if t.scores["subscores"].get(k) is not None]
        if vals:
            sub_avg[k] = round(mean(vals), 1)
    overall = round(mean(t.scores["total"] for t in scored) * 10)
    ranked = sorted(sub_avg.items(), key=lambda kv: kv[1])
    strengths = [f"{LABEL[k]} ({v}/10)" for k, v in reversed(ranked) if v >= 7][:2]
    fixes = [{"area": LABEL[k], "score": v, "tip": pack.tips.get(k, "")} for k, v in ranked if v < 7.5][:3]

    flags = [dict(f, question=t.question_text) for t in scored for f in t.scores.get("flags", [])]
    voice = [t.metrics for t in scored if t.metrics and "words_per_minute" in t.metrics]
    delivery = None
    if voice:
        delivery = {
            "avg_words_per_minute": round(mean(m["words_per_minute"] for m in voice)),
            "filler_total": sum(m["filler_total"] for m in voice),
            "long_pauses": sum(m.get("long_pauses", 0) for m in voice),
        }
    by_q: dict[str, list[float]] = {}
    for t in scored:
        by_q.setdefault(t.question_id, []).append(t.scores["total"])
    weakest = sorted(by_q, key=lambda q: mean(by_q[q]))[:2]

    band = "Ready" if overall >= 80 else "Nearly there" if overall >= 65 else "Needs practice"
    return {
        "overall": overall,
        "band": band,
        "subscores": sub_avg,
        "strengths": strengths,
        "fixes": fixes,
        "flags": flags,
        "delivery": delivery,
        "practise_again": weakest,
        "judge": judge_name,
        "answered": len(scored),
        "per_question": [
            {
                "turn_id": t.id,
                "question": t.question_text,
                "is_follow_up": t.is_follow_up,
                "total": t.scores["total"],
                "subscores": t.scores["subscores"],
                "strength": t.scores.get("strength", ""),
                "improvement": t.scores.get("improvement", ""),
            }
            for t in scored
        ],
        "disclaimer": "Practice estimate only. Real interviews are judged by people, on your honest answers.",
    }
