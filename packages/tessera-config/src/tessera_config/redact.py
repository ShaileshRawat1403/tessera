"""Secret detection and masking for config values.

Kept local to this pack (a ~handful of lines) rather than imported from another
pack: packs do not depend on each other. Same masking contract as elsewhere in
the hub: reveal at most a couple of leading characters and the length, never
the tail.
"""

from __future__ import annotations

import re

_SECRET_NAME_RE = re.compile(
    r"(secret|token|password|passwd|pwd|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|client[_-]?secret|auth|credential|signing|sas|"
    r"session|cookie)",
    re.IGNORECASE,
)


def is_secret_name(name: str) -> bool:
    return bool(_SECRET_NAME_RE.search(name or ""))


def mask(value: str, lead: int = 2) -> str:
    value = value or ""
    n = len(value)
    if n == 0:
        return ""
    if n <= lead:
        return f"…(redacted, len={n})"
    return f"{value[:lead]}…(redacted, len={n})"


import math  # noqa: E402

# High-confidence provider token patterns (kept local; packs do not import each
# other). Catches a secret VALUE even when the KEY name is innocuous.
_TOKEN_PATTERNS = [
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe_key", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
]
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts: dict[str, int] = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def detect_secret_shape(value: str) -> str | None:
    """Return a secret-kind label if the value looks like a secret, else None."""
    v = (value or "").strip()
    if not v:
        return None
    for kind, pat in _TOKEN_PATTERNS:
        if pat.search(v):
            return kind
    if _UUID_RE.fullmatch(v):
        return None
    if len(v) >= 24 and " " not in v and "/" not in v and not v.startswith(("http://", "https://")):
        if re.fullmatch(r"[A-Za-z0-9+/=_\-\.]+", v) and _entropy(v) >= 3.5:
            return "high_entropy_value"
    return None
