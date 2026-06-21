"""Secret detection and masking.

The contract for this module: given a raw value that may be a secret, return a
masked preview that reveals at most a few leading characters and never the tail.
All redaction happens before a value is written into an ``ApiRequest``; the
canonical record and every artifact hold only masked previews.
"""

from __future__ import annotations

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
