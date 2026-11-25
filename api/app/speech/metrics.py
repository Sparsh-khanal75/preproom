"""Delivery metrics from a transcript: pace, pauses and filler words."""

from __future__ import annotations

import re

FILLERS = [
    "um",
    "umm",
    "uh",
    "uhh",
    "erm",
    "er",
    "hmm",
    "you know",
    "i mean",
    "kind of",
    "sort of",
    "basically",
    "actually",
    "literally",
]
_FILLER_RE = re.compile(r"\b(" + "|".join(re.escape(f) for f in sorted(FILLERS, key=len, reverse=True)) + r")\b", re.I)
LONG_PAUSE_S = 2.0


def filler_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in _FILLER_RE.finditer(text):
        k = m.group(1).lower()
        counts[k] = counts.get(k, 0) + 1
    return counts


def speech_metrics(text: str, words: list[dict] | None, duration: float | None) -> dict:
    """For voice answers (word timestamps available) and text answers (length only)."""
    n = len(text.split())
    fillers = filler_counts(text)
    m: dict = {"word_count": n, "fillers": fillers, "filler_total": sum(fillers.values())}
    if words:
        spoken = max(words[-1]["end"] - words[0]["start"], 0.1)
        gaps = [round(b["start"] - a["end"], 2) for a, b in zip(words, words[1:], strict=False)]
        pauses = [g for g in gaps if g >= LONG_PAUSE_S]
        m.update(
            duration_s=round(duration or spoken, 1),
            words_per_minute=round(len(words) / spoken * 60, 1),
            long_pauses=len(pauses),
            longest_pause_s=max(gaps, default=0.0),
            fillers_per_minute=round(m["filler_total"] / spoken * 60, 2),
        )
    return m
