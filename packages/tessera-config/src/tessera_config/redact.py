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
