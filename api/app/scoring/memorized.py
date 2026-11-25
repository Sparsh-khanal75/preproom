"""Flags answers that sound memorised or generic, using TF-IDF similarity (no model download)."""

from __future__ import annotations

import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

GENERIC_PHRASES = [
    "passionate about",
    "since my childhood",
    "world-class",
    "world class",
    "prestigious",
    "multicultural environment",
    "achieve my dreams",
    "reputed company",
    "one of the best universities",
    "recognised all over the world",
    "recognized all over the world",
    "hard working",
    "hard-working",
    "team player",
    "give my best",
    "golden opportunity",
    "dream university",
    "excellent faculty",
    "state of the art",
    "state-of-the-art",
]
THRESHOLD = 0.45


@lru_cache(maxsize=64)
def _vectoriser(corpus: tuple[str, ...]):
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
    matrix = vec.fit_transform(corpus)
    return vec, matrix


def generic_check(answer: str, generic_answers: list[str]) -> dict:
    low = answer.lower()
    phrases = [p for p in GENERIC_PHRASES if p in low]
    similarity = 0.0
    closest = None
    if generic_answers and len(re.findall(r"\w+", answer)) >= 5:
        vec, matrix = _vectoriser(tuple(generic_answers))
        sims = cosine_similarity(vec.transform([answer]), matrix)[0]
        i = int(sims.argmax())
        similarity, closest = float(sims[i]), generic_answers[i]
    flagged = similarity >= THRESHOLD or len(phrases) >= 2
    return {
        "flagged": flagged,
        "similarity": round(similarity, 2),
        "closest_generic": closest if flagged else None,
        "phrases": phrases,
    }
