"""Secret detection and masking.

The contract for this module: given a raw value that may be a secret, return a
masked preview that reveals at most a few leading characters and never the tail.
All redaction happens before a value is written into an ``ApiRequest``; the
canonical record and every artifact hold only masked previews.
"""

from __future__ import annotations

import math
import re

# Header names whose values are always treated as secret.
SECRET_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "x-auth-token",
    "x-auth",
    "x-access-token",
    "x-secret",
    "x-amz-security-token",
    "cookie",
    "set-cookie",
}

# Query parameter names whose values are always treated as secret.
SECRET_QUERY_NAMES = {
    "api_key",
    "apikey",
    "key",
    "token",
    "access_token",
    "auth",
    "auth_token",
    "secret",
    "client_secret",
    "password",
    "passwd",
    "pwd",
    "sig",
    "signature",
    "sas",
}

_MASK = "(redacted"


def mask(value: str, lead: int = 2) -> str:
    """Return a masked preview: a few leading chars plus length, never the tail."""
    value = value or ""
    n = len(value)
    if n == 0:
        return "(redacted, empty)"
    if n <= lead:
        return f"…(redacted, len={n})"
    return f"{value[:lead]}…(redacted, len={n})"


def is_secret_header(name: str) -> bool:
    return name.strip().lower() in SECRET_HEADER_NAMES


def is_secret_query(name: str) -> bool:
    return name.strip().lower() in SECRET_QUERY_NAMES


def classify_header_secret(name: str, value: str) -> str:
    """Return a redaction kind label for a secret header value."""
    lname = name.strip().lower()
    if lname in ("authorization", "proxy-authorization"):
        low = value.strip().lower()
        if low.startswith("bearer "):
            return "bearer_token"
        if low.startswith("basic "):
            return "basic_credentials"
        return "authorization_value"
    if lname in ("cookie", "set-cookie"):
        return "cookie"
    return "api_key"


def auth_token_value(value: str) -> str:
    """Strip the scheme prefix (Bearer/Basic) so we mask only the credential."""
    m = re.match(r"^\s*(bearer|basic)\s+(.*)$", value, re.IGNORECASE)
    if m:
        return m.group(2)
    return value


# --- shape-based secret detection -------------------------------------------
# High-confidence provider token patterns: (kind, pattern). These catch secrets
# regardless of the field name they appear in.
_TOKEN_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe_key", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
]


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts: dict[str, int] = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def detect_secret_shape(value: str) -> str | None:
    """Return a secret-kind label if the value *looks* like a secret, else None.

    First tries precise provider patterns, then a conservative high-entropy
    heuristic for long, space-free, mixed-charset tokens.
    """
    v = (value or "").strip()
    if not v:
        return None
    for kind, pat in _TOKEN_PATTERNS:
        if pat.search(v):
            return kind
    # Common non-secret identifiers that would otherwise look high-entropy.
    if _UUID_RE.fullmatch(v):
        return None
    # entropy fallback: long, no spaces, looks token-ish (not a sentence/URL/path)
    if len(v) >= 24 and " " not in v and "/" not in v and not v.startswith(("http://", "https://")):
        token_chars = re.fullmatch(r"[A-Za-z0-9+/=_\-\.]+", v)
        if token_chars and _shannon_entropy(v) >= 3.5:
            return "high_entropy_value"
    return None


_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
