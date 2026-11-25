"""Deterministic, explainable checks. These run with or without an LLM and keep the LLM honest."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..packs.schema import Pack, Question

MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
NUMBER_RE = re.compile(
    r"(?<![\w.])(?:[£$€₹]|rs\.?\s?|npr\s?|cad\s?|usd\s?|gbp\s?)?\d[\d,]*(?:\.\d+)?\s?(?:k|%|percent|"
    r"thousand|lakh|million)?(?![\w])",
    re.I,
)
DATE_RE = re.compile(rf"\b(?:{MONTHS})\b(?:\s+\d{{4}})?|\b(?:19|20)\d{{2}}\b", re.I)
PROPER_RE = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-zA-Z]+(?:\s+(?:of|and|for|the|&)?\s*[A-Z][a-zA-Z]+)*")
STOP_CAPS = {
    "I",
    "I'm",
    "I've",
    "I'll",
    "My",
    "The",
    "This",
    "That",
    "It",
    "And",
    "But",
    "So",
    "Because",
    "We",
    "In",
    "On",
    "At",
    "After",
    "Before",
    "Also",
    "Then",
    "When",
    "If",
    "As",
    "For",
    "To",
    "A",
    "An",
}
WORD_RE = re.compile(r"[a-z0-9']+")


@dataclass
class Contradiction:
    field: str
    said: str
    profile_value: str
    explanation: str
    source: str = "rule"


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def norm(text: str) -> str:
    return " ".join(words(text))


def mentions(answer: str, value: str) -> bool:
    """True if the answer names the value (case/punctuation-insensitive), or most of its distinctive words."""
    a, v = norm(answer), norm(value)
    if not v:
        return False
    if v in a:
        return True
    vw = [w for w in v.split() if len(w) > 3 and w not in {"university", "college", "msc", "bsc", "with"}]
    return bool(vw) and sum(w in a.split() for w in vw) / len(vw) >= 0.6


def specific_details(answer: str, profile: dict) -> list[str]:
    """Concrete details: numbers, dates, proper names, and profile facts the candidate named."""
    found: list[str] = []
    found += [m.group(0).strip() for m in NUMBER_RE.finditer(answer)]
    found += [m.group(0) for m in DATE_RE.finditer(answer)]
    for sent in re.split(r"(?<=[.!?])\s+", answer):
        for m in PROPER_RE.finditer(sent):
            phrase = m.group(0).strip()
            if m.start() == 0 and len(phrase.split()) == 1:
                continue  # first word of a sentence
            if phrase not in STOP_CAPS and len(phrase) > 2:
                found.append(phrase)
    for v in profile.values():
        for item in v if isinstance(v, list) else [v]:
            if isinstance(item, str) and len(item) > 3 and mentions(answer, item):
                found.append(item)
    seen, out = set(), []
    for f in found:
        k = f.lower()
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def keyword_coverage(answer: str, expects: list[str]) -> tuple[float, list[str]]:
    """Share of expected topic keywords the answer touches (prefix match, so 'fund' hits 'funding')."""
    if not expects:
        return 1.0, []
    a = norm(answer)
    toks = a.split()
    hit = []
    for kw in expects:
        k = norm(kw)
        if (" " in k and k in a) or any(t.startswith(k[: max(4, len(k) - 2)]) for t in toks):
            hit.append(kw)
    return len(hit) / len(expects), hit


def _to_number(token: str) -> float | None:
    t = token.lower().replace(",", "").strip()
    t = re.sub(r"^(?:[£$€₹]|rs\.?\s?|npr\s?|cad\s?|usd\s?|gbp\s?)", "", t)
    mult = 1.0
    for suf, f in (("thousand", 1e3), ("lakh", 1e5), ("million", 1e6), ("k", 1e3)):
        if t.endswith(suf):
            t, mult = t[: -len(suf)].strip(), f
            break
    if t.endswith(("%", "percent")):
        return None
    try:
        return float(t) * mult
    except ValueError:
        return None


def numeric_contradictions(answer: str, profile: dict, pack: Pack, q: Question) -> list[Contradiction]:
    """A number in the answer that is clearly a different value for a numeric profile fact (e.g. the fee)."""
    out = []
    numeric = {f.id: f for f in pack.profile_fields if f.type == "number"}
    for fid in q.profile_fields:
        if fid not in numeric or profile.get(fid) in (None, ""):
            continue
        try:
            truth = float(str(profile[fid]).replace(",", ""))
        except ValueError:
            continue
        said = [(m.group(0), _to_number(m.group(0))) for m in NUMBER_RE.finditer(answer)]
        said = [(raw, v) for raw, v in said if v and truth * 0.25 <= v <= truth * 4]  # same order of magnitude
        if said and not any(abs(v - truth) / truth <= 0.1 for _, v in said):
            raw = said[0][0]
            out.append(
                Contradiction(fid, raw, str(profile[fid]), f"You said {raw.strip()}, but your profile says {profile[fid]}.")
            )
    return out


def entity_contradictions(answer: str, profile: dict, pack: Pack, q: Question) -> list[Contradiction]:
    """Naming a different entity of the same kind, e.g. 'University of Leeds' when the profile says Manchester."""
    out = []
    entities = {f.id: f for f in pack.profile_fields if f.entity}
    for fid in q.profile_fields:
        value = str(profile.get(fid) or "").strip()
        if fid not in entities or not value or mentions(answer, value):
            continue
        kind_words = [
            w
            for w in value.split()
            if w.lower() in {"university", "college", "institute", "school", "academy", "bank", "ltd", "inc"}
        ]
        if not kind_words:
            continue
        for m in PROPER_RE.finditer(answer):
            phrase = m.group(0)
            if any(k in phrase for k in kind_words) and len(phrase.split()) >= 2 and not mentions(phrase, value):
                out.append(Contradiction(fid, phrase, value, f"You named {phrase}, but your profile says {value}."))
                break
    return out


def language_heuristic(answer: str) -> tuple[float, list[str]]:
    """Rough 0-10 language score used only when no LLM is available."""
    notes: list[str] = []
    sents = [s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s]
    w = answer.split()
    if not w:
        return 0.0, ["empty answer"]
    score = 8.0
    avg = len(w) / max(len(sents), 1)
    if avg > 35:
        score -= 2
        notes.append("very long sentences - split them")
    if re.search(r"\bi\b", answer):
        score -= 1
        notes.append("lower-case 'i'")
    reps = [x for x in set(t.lower() for t in w if len(t) > 4) if sum(t.lower() == x for t in w) >= 4]
    if reps:
        score -= 1
        notes.append(f"repeated words: {', '.join(sorted(reps)[:3])}")
    return max(score, 2.0), notes
