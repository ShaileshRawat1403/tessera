from __future__ import annotations

import re

_BASH_FENCE_RE = re.compile(r"```(?:bash|sh|shell|zsh)\s*\n(.*?)```", re.DOTALL)
_MCP_TOOL_RE = re.compile(r"\b(mcp__[a-zA-Z0-9_]+)\b")
_SKILL_REF_RE = re.compile(r"(?<![\w/])/([a-z][a-z0-9-]+)(?![\w/])")

_BASH_FIRST_WORD_RE = re.compile(r"^\s*([a-zA-Z][\w./-]*)")


def extract_bash_commands(body: str) -> list[str]:
    """Return distinct first-word commands found in bash code fences."""
    found: set[str] = set()
    for fence in _BASH_FENCE_RE.findall(body):
        for line in fence.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("$ "):
                stripped = stripped[2:]
            m = _BASH_FIRST_WORD_RE.match(stripped)
            if m:
                cmd = m.group(1)
                if cmd in {"export", "cd", "set", "unset"}:
                    continue
                found.add(cmd)
    return sorted(found)


def extract_mcp_tools(body: str) -> list[str]:
    return sorted(set(_MCP_TOOL_RE.findall(body)))


def extract_skill_refs(body: str, own_name: str | None = None) -> list[str]:
    """Return skill slugs referenced via /<slug> form. Excludes the skill's own name."""
    raw = _SKILL_REF_RE.findall(body)
    out = {slug for slug in raw if slug != own_name}
    return sorted(out)
