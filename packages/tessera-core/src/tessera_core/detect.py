from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from dataclasses import field as dc_field
from difflib import SequenceMatcher
from typing import Iterable


@dataclass
class ColumnDetection:
    field: str
    column: str | None
    confidence: float
    reason: str
    candidates: list[str] = dc_field(default_factory=list)


@dataclass
class ColumnAnalysis:
    column: str
    total: int
    non_empty: int
    completeness: float
    avg_length: float
    max_length: int
    inferred_type: str
    distinct: int
    examples: list[str] = dc_field(default_factory=list)


_TOKEN_RE = re.compile(r"[a-z0-9]+")

_HEADER_PREFIXES = {
    "customer", "user", "agent", "support", "ai", "model", "llm", "gpt",
    "the", "our", "your", "my", "their", "his", "her",
    "raw", "original", "input",
}
_HEADER_SUFFIXES = {
    "text", "field", "column", "value", "data", "str", "string",
    "content", "body", "msg",
    # v0.2: compound-header normalization — "expected_output" -> "expected", "ground_truth_answer" -> "ground_truth"
    "output", "answer", "result",
}

_FUZZY_THRESHOLD = 0.82  # SequenceMatcher ratio; catches 1-2 char typos in typical field names


def _fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _normalize_header(header: str) -> str:
    """Strip common wrapper prefixes and suffixes; return the canonical core."""
    parts = _tokens(header)
    while len(parts) > 1 and parts[0] in _HEADER_PREFIXES:
        parts = parts[1:]
    while len(parts) > 1 and parts[-1] in _HEADER_SUFFIXES:
        parts = parts[:-1]
    return "_".join(parts) if parts else header.lower()


def detect_column(
    headers: list[str],
    field: str,
    candidates: list[str],
    override: str | None = None,
) -> ColumnDetection:
    """Pick the best header for ``field`` from a candidate list.

    Confidence tiers:
      1.00  manual override (validated against headers)
      0.95  exact match (raw or normalized)
      0.85  token match (candidate is a token of the header)
      0.75  fuzzy match (edit-distance >= 0.82; catches typos)
      0.70  substring match
      0.00  no match
    """
    if override is not None:
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

    candidate_set = [c.lower() for c in candidates]
    lowered = {h.lower().strip(): h for h in headers}

    for cand in candidate_set:
        if cand in lowered:
            return ColumnDetection(
                field=field,
                column=lowered[cand],
                confidence=0.95,
                reason=f"exact match: {cand}",
                candidates=candidates,
            )

    normalized = {_normalize_header(h): h for h in headers}
    for cand in candidate_set:
        if cand in normalized:
            return ColumnDetection(
                field=field,
                column=normalized[cand],
                confidence=0.95,
                reason=f"normalized match: {normalized[cand]} -> {cand}",
                candidates=candidates,
            )

    best: tuple[float, str | None, str] = (0.0, None, "no match")
    for header in headers:
        header_tokens = set(_tokens(header))
        header_lower = header.lower()
        header_norm = _normalize_header(header)
        for cand in candidate_set:
            cand_tokens = set(_tokens(cand))
            if cand_tokens and cand_tokens.issubset(header_tokens):
                score, reason = 0.85, f"token match: {cand}"
            elif cand in header_lower:
                score, reason = 0.70, f"substring match: {cand}"
            else:
                # fuzzy: compare normalized header against each token of the candidate
                cand_norm = _normalize_header(cand)
                ratio = max(
                    _fuzzy_score(header_lower, cand),
                    _fuzzy_score(header_norm, cand_norm),
                )
                if ratio >= _FUZZY_THRESHOLD:
                    score = 0.75
                    reason = f"fuzzy match: {cand} (ratio {ratio:.2f})"
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


def detect_by_content(
    rows: list[dict[str, str]],
    headers: list[str],
    field: str,
    candidates: list[str],
    exclude_columns: Iterable[str] = (),
    min_avg_length: int = 20,
) -> ColumnDetection:
    """Content-based fallback: pick the column with the longest average text.

    Used only when ``detect_column`` returns confidence 0.0. Capped at 0.40
    because we are inferring from data shape, not semantics. The caller should
    surface this as a low-confidence warning in the quality report.
    """
    excluded = set(exclude_columns)
    scored: list[tuple[str, float]] = []
    for header in headers:
        if header in excluded:
            continue
        non_empty_lengths = [
            len(str(row.get(header, "")).strip())
            for row in rows
            if str(row.get(header, "")).strip()
        ]
        if not non_empty_lengths:
            continue
        avg = statistics.mean(non_empty_lengths)
        if avg < min_avg_length:
            continue
        scored.append((header, avg))

    if not scored:
        return ColumnDetection(
            field=field,
            column=None,
            confidence=0.0,
            reason="content fallback found no free-text columns",
            candidates=list(candidates),
        )

    scored.sort(key=lambda x: x[1], reverse=True)
    picked, avg = scored[0]
    return ColumnDetection(
        field=field,
        column=picked,
        confidence=0.40,
        reason=f"content fallback: longest text column (avg {avg:.0f} chars)",
        candidates=list(candidates),
    )


def analyze_column(rows: list[dict[str, str]], column: str) -> ColumnAnalysis:
    """Profile a column: completeness, length, type inference, distinct count."""
    total = len(rows)
    values = [str(row.get(column, "")).strip() for row in rows]
    non_empty = [v for v in values if v]
    n_non_empty = len(non_empty)
    distinct = len(set(non_empty))

    if not non_empty:
        return ColumnAnalysis(
            column=column,
            total=total,
            non_empty=0,
            completeness=0.0,
            avg_length=0.0,
            max_length=0,
            inferred_type="empty",
            distinct=0,
            examples=[],
        )

    lengths = [len(v) for v in non_empty]
    avg_len = statistics.mean(lengths)
    max_len = max(lengths)

    numeric_count = sum(1 for v in non_empty if _looks_numeric(v))
    if numeric_count == n_non_empty:
        inferred = "numeric"
    elif distinct <= max(2, n_non_empty // 5) and max_len <= 40:
        inferred = "category"
    elif avg_len > 30:
        inferred = "text"
    else:
        inferred = "short"

    return ColumnAnalysis(
        column=column,
        total=total,
        non_empty=n_non_empty,
        completeness=n_non_empty / total if total else 0.0,
        avg_length=avg_len,
        max_length=max_len,
        inferred_type=inferred,
        distinct=distinct,
        examples=non_empty[:3],
    )


def _looks_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False
