from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ColumnDetection:
    field: str
    column: str | None
    confidence: float
    reason: str
    candidates: list[str] = field(default_factory=list)


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def detect_column(
    headers: list[str],
    field: str,
    candidates: list[str],
    override: str | None = None,
) -> ColumnDetection:
    """Pick the best header for ``field`` from a candidate list.

    Confidence levels:
      1.00 — manual override
      0.95 — exact match (header == candidate, case-insensitive)
      0.85 — candidate is a token of the header (e.g. "question" in "customer_question")
      0.70 — candidate appears as substring of the header
      0.00 — no match
    """
    if override:
        if override in headers:
            return ColumnDetection(
                field=field,
                column=override,
                confidence=1.0,
                reason=f"manual override: --{field.replace('_', '-')}-column={override}",
                candidates=candidates,
            )
        return ColumnDetection(
            field=field,
            column=None,
            confidence=0.0,
            reason=f"override column '{override}' not found in headers",
            candidates=candidates,
        )

    lowered = {h.lower().strip(): h for h in headers}
    candidate_set = [c.lower() for c in candidates]

    for cand in candidate_set:
        if cand in lowered:
            return ColumnDetection(
                field=field,
                column=lowered[cand],
                confidence=0.95,
                reason=f"exact match: {cand}",
                candidates=candidates,
            )

    best: tuple[float, str | None, str] = (0.0, None, "no match")
    for header in headers:
        header_tokens = _tokens(header)
        header_lower = header.lower()
        for cand in candidate_set:
            cand_tokens = _tokens(cand)
            if cand_tokens and cand_tokens.issubset(header_tokens):
                score = 0.85
                reason = f"token match: {cand}"
            elif cand in header_lower:
                score = 0.70
                reason = f"substring match: {cand}"
            else:
                continue
            if score > best[0]:
                best = (score, header, reason)

    return ColumnDetection(
        field=field,
        column=best[1],
        confidence=best[0],
        reason=best[2],
        candidates=candidates,
    )
