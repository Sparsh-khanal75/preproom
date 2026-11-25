"""Combine rule checks, speech metrics and the (verified) LLM verdict into explainable sub-scores."""

from __future__ import annotations

from typing import Any

from ..packs.schema import SUBSCORES, Pack, Question
from . import checks
from .judge import Verdict
from .memorized import generic_check


def _clamp(x: float) -> float:
    return round(max(0.0, min(10.0, x)), 1)


def relevant_profile(profile: dict, q: Question) -> dict:
    return {k: profile[k] for k in q.profile_fields if profile.get(k) not in (None, "", [])}


def score_answer(
    pack: Pack, q: Question, profile: dict, answer: str, metrics: dict, verdict: Verdict | None, judge_note: str = ""
) -> dict[str, Any]:
    sub: dict[str, float | None] = {}
    evidence: dict[str, list[str]] = {k: [] for k in SUBSCORES}
    flags: list[dict] = []
    n_words = metrics.get("word_count", len(answer.split()))
    rel_profile = relevant_profile(profile, q)

    # --- consistency --------------------------------------------------------------------
    contradictions = checks.numeric_contradictions(answer, profile, pack, q)
    contradictions += checks.entity_contradictions(answer, profile, pack, q)
    if verdict:
        for c in verdict.contradictions:
            if not any(x.field == c.field for x in contradictions):
                contradictions.append(checks.Contradiction(c.field, c.quote, str(profile.get(c.field, "")), c.explanation, "llm"))
    if rel_profile:
        cons = 10.0
        entity_fields = [f.id for f in pack.profile_fields if f.entity and f.id in rel_profile]
        named = [f for f in entity_fields if checks.mentions(answer, str(rel_profile[f]))]
        if entity_fields and not named:
            cons -= 1.5
            evidence["consistency"].append(f"Didn't name your {', '.join(entity_fields).replace('_', ' ')} explicitly.")
        for c in contradictions:
            evidence["consistency"].append(c.explanation)
            flags.append(
                {
                    "type": "contradiction",
                    "field": c.field,
                    "said": c.said,
                    "profile": c.profile_value,
                    "source": c.source,
                }
            )
        if contradictions:
            cons = min(cons, 3.0)
        if not evidence["consistency"]:
            evidence["consistency"].append("Consistent with your profile.")
        sub["consistency"] = _clamp(cons)
    else:
        sub["consistency"] = None

    # --- specificity --------------------------------------------------------------------
    details = checks.specific_details(answer, profile)
    rule_spec = 2.5 + 1.5 * len(details)
    sub["specificity"] = _clamp(0.5 * rule_spec + 0.5 * verdict.specificity) if verdict else _clamp(rule_spec)
    evidence["specificity"].append(
        f"Concrete details: {', '.join(d if len(d) <= 40 else d[:37] + '...' for d in details[:6])}"
        if details
        else "No names, numbers or dates."
    )
    generic = generic_check(answer, pack.generic_answers)
    if generic["flagged"]:
        sub["specificity"] = _clamp(sub["specificity"] - 2)
        why = f"phrases like '{generic['phrases'][0]}'" if generic["phrases"] else "very close to a template answer"
        evidence["specificity"].append(f"Sounds generic or memorised ({why}).")
        flags.append({"type": "generic", **generic})

    # --- relevance ----------------------------------------------------------------------
    coverage, hit = checks.keyword_coverage(answer, q.expects)
    rule_rel = 3 + 7 * min(coverage / 0.5, 1.0)
    rel = 0.4 * rule_rel + 0.6 * verdict.relevance if verdict else rule_rel
    if n_words < pack.min_answer_words:
        rel = min(rel, 6.0)
        evidence["relevance"].append(f"Short answer ({n_words} words; aim for {pack.min_answer_words}+).")
    if verdict and verdict.relevance_reason:
        evidence["relevance"].append(verdict.relevance_reason)
    evidence["relevance"].append(f"Covered: {', '.join(hit)}" if hit else "Didn't touch the expected topics.")
    sub["relevance"] = _clamp(rel)

    # --- fluency (voice answers only) ---------------------------------------------------
    if "words_per_minute" in metrics:
        flu = 10.0
        wpm = metrics["words_per_minute"]
        if wpm < 110 or wpm > 160:
            off = (110 - wpm) if wpm < 110 else (wpm - 160)
            flu -= min(4.0, off / 15)
            evidence["fluency"].append(f"Pace {wpm:.0f} wpm (aim for 110-160).")
        else:
            evidence["fluency"].append(f"Good pace: {wpm:.0f} wpm.")
        if metrics.get("long_pauses"):
            flu -= min(3.0, 0.75 * metrics["long_pauses"])
            evidence["fluency"].append(f"{metrics['long_pauses']} pause(s) over 2 s.")
        fpm = metrics.get("fillers_per_minute", 0)
        if fpm > 3:
            flu -= min(3.0, (fpm - 3) * 0.5)
            top = ", ".join(f"'{k}' x{v}" for k, v in sorted(metrics["fillers"].items(), key=lambda kv: -kv[1])[:3])
            evidence["fluency"].append(f"{fpm:.1f} filler words per minute ({top}).")
        sub["fluency"] = _clamp(flu)
    else:
        sub["fluency"] = None
        evidence["fluency"].append("Typed answer - fluency not measured.")

    # --- language -----------------------------------------------------------------------
    rule_lang, notes = checks.language_heuristic(answer)
    if verdict:
        lang = 0.3 * rule_lang + 0.7 * verdict.language
        evidence["language"] += [f"'{c.quote}' -> '{c.better}'" for c in verdict.corrections]
    else:
        lang = rule_lang
    evidence["language"] += notes or ([] if verdict and verdict.corrections else ["No issues found."])
    sub["language"] = _clamp(lang)

    # --- weighted total (sub-scores that don't apply are dropped and weights renormalised) --
    weights = {k: w for k, w in pack.rubric.items() if sub.get(k) is not None and w > 0}
    total = sum(sub[k] * w for k, w in weights.items()) / sum(weights.values()) if weights else 0.0

    # spans the UI underlines in the transcript (only text that really occurs in the answer)
    highlights: list[dict[str, str]] = []
    low = answer.lower()
    for d in details:
        if len(d) <= 60 and d.lower() in low:
            highlights.append({"text": d, "kind": "detail"})
    for c in contradictions:
        if c.said and c.said.lower() in low:
            highlights.append({"text": c.said, "kind": "contradiction", "note": c.explanation})
    for p in generic["phrases"]:
        highlights.append({"text": p, "kind": "generic", "note": "Sounds generic - say it in your own words"})
    if verdict:
        for c in verdict.corrections:
            highlights.append({"text": c.quote, "kind": "language", "note": f"Try: {c.better}"})

    return {
        "highlights": highlights,
        "subscores": sub,
        "total": _clamp(total),
        "evidence": evidence,
        "flags": flags,
        "strength": verdict.strength if verdict else "",
        "improvement": verdict.improvement if verdict else "",
        "judge": "llm+rules" if verdict else "rules",
        "judge_note": judge_note,
    }
