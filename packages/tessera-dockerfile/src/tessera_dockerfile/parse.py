"""Parse Dockerfiles into instructions (handles line continuations + comments)."""

from __future__ import annotations

import re
from pathlib import Path

from tessera_dockerfile.schema import Instruction

_DOCKERFILE_NAMES = ("dockerfile",)
_INSTR_RE = re.compile(r"^\s*([A-Za-z]+)\s+(.*)$", re.DOTALL)
_FROM_AS_RE = re.compile(r"\bAS\s+([A-Za-z0-9_.-]+)\s*$", re.IGNORECASE)


def is_dockerfile(path: Path) -> bool:
    n = path.name.lower()
    return n in _DOCKERFILE_NAMES or n.startswith("dockerfile.") or n.endswith(".dockerfile")


def discover_dockerfiles(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and is_dockerfile(p):
            if not any(part in {".git", ".venv", "node_modules", "dist", "build"} for part in p.relative_to(root).parts):
                out.append(p)
    return out


def parse_dockerfile(path: Path, rel: str) -> list[Instruction]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # join line continuations
    logical: list[tuple[int, str]] = []
    buf: list[str] = []
    start = 0
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not buf and (not stripped or stripped.startswith("#")):
            continue
        if not buf:
            start = i
        if line.rstrip().endswith("\\"):
            buf.append(line.rstrip()[:-1])
        else:
            buf.append(line)
            logical.append((start, " ".join(s.strip() for s in buf)))
            buf = []
    if buf:
        logical.append((start, " ".join(s.strip() for s in buf)))

    instructions: list[Instruction] = []
    current_stage = ""
    for lineno, line in logical:
        m = _INSTR_RE.match(line)
        if not m:
            continue
        instr = m.group(1).upper()
        arg = m.group(2).strip()
        stage = current_stage
        if instr == "FROM":
            am = _FROM_AS_RE.search(arg)
            current_stage = am.group(1) if am else ""
            stage = current_stage
        instructions.append(Instruction(instruction=instr, argument=arg, file=rel, lineno=lineno, stage=stage))
    return instructions
