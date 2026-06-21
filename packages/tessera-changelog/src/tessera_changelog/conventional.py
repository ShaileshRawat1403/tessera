"""Conventional Commits parsing."""

from __future__ import annotations

import re

KNOWN_TYPES = {
    "feat", "fix", "docs", "refactor", "perf", "test",
    "build", "ci", "chore", "style", "revert",
}

# type(scope)!: description   /   type!: description   /   type: description
_HEADER_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")
_PR_RE = re.compile(r"\(#(\d+)\)\s*$|#(\d+)\b")


def parse_subject(subject: str, body: str = "") -> dict:
    """Return parsed fields: type, scope, breaking, conventional, description, pr_number."""
    subject = (subject or "").strip()
    pr = ""
    m_pr = _PR_RE.search(subject)
    if m_pr:
        pr = m_pr.group(1) or m_pr.group(2) or ""

    breaking = "BREAKING CHANGE" in body or "BREAKING-CHANGE" in body

    m = _HEADER_RE.match(subject)
    if not m or m.group("type").lower() not in KNOWN_TYPES:
        return {
            "type": "other",
            "scope": "",
            "breaking": breaking,
            "conventional": False,
            "description": subject,
            "pr_number": pr,
        }

    ctype = m.group("type").lower()
    if m.group("bang"):
        breaking = True
    return {
        "type": ctype,
        "scope": (m.group("scope") or "").strip(),
        "breaking": breaking,
        "conventional": True,
        "description": m.group("desc").strip(),
        "pr_number": pr,
    }
