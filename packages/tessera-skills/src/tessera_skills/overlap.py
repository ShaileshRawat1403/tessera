from __future__ import annotations

import re
from dataclasses import dataclass

from tessera_skills.schema import SkillManifest

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common English + skill-conventional stopwords.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were",
    "be", "been", "being", "to", "of", "in", "on", "at", "for", "with",
    "by", "from", "this", "that", "these", "those",
    "use", "uses", "used", "using", "when", "while", "if", "then",
    "it", "its", "as", "into", "about", "you", "your", "should",
    "can", "will", "may", "might", "such",
}


@dataclass
class OverlapPair:
    name_a: str
    name_b: str
    similarity: float
    severity: str  # "warning" or "error"


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_overlaps(
    skills: list[SkillManifest],
    warn_threshold: float = 0.5,
    error_threshold: float = 0.7,
) -> list[OverlapPair]:
    """Return all pairs whose description token-similarity exceeds the warn threshold."""
    pairs: list[OverlapPair] = []
    token_sets = [(s.name, _tokens(s.description)) for s in skills]
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            name_a, set_a = token_sets[i]
            name_b, set_b = token_sets[j]
            sim = jaccard(set_a, set_b)
            if sim >= error_threshold:
                pairs.append(OverlapPair(name_a, name_b, sim, "error"))
            elif sim >= warn_threshold:
                pairs.append(OverlapPair(name_a, name_b, sim, "warning"))
    return pairs
