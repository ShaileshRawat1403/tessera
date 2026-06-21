"""Read commit history from a git repository (read-only; no network)."""

from __future__ import annotations

import subprocess
from pathlib import Path

_US = "\x1f"  # unit separator between fields
_RS = "\x1e"  # record separator between commits


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def read_git_log(repo: Path, since: str | None = None, max_count: int | None = None) -> list[dict]:
    """Return commit dicts via `git log`. Raises RuntimeError on git failure."""
    fmt = _US.join(["%H", "%h", "%an", "%aI", "%s", "%b"]) + _RS
    cmd = ["git", "-C", str(repo), "log", f"--pretty=format:{fmt}", "--no-merges"]
    if max_count:
        cmd.append(f"-n{max_count}")
    if since:
        cmd.append(f"{since}..HEAD")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:  # git not installed
        raise RuntimeError("git executable not found") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git log failed: {exc.stderr.strip()}") from exc

    commits: list[dict] = []
    for chunk in result.stdout.split(_RS):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        fields = chunk.split(_US)
        if len(fields) < 5:
            continue
        full, short, author, date, subject = fields[:5]
        body = fields[5] if len(fields) > 5 else ""
        commits.append({
            "hash": full.strip(),
            "short_hash": short.strip(),
            "author": author.strip(),
            "date": date.strip(),
            "subject": subject.strip(),
            "body": body.strip(),
        })
    return commits
