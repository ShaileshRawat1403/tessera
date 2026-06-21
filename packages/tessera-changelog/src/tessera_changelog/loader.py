from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tessera_changelog.conventional import parse_subject
from tessera_changelog.gitlog import is_git_repo, read_git_log
from tessera_changelog.schema import Commit


def load_changelog_records(input_path: Path, options: dict[str, Any]) -> list[Commit]:
    """Load commits from a git repo or a commits.jsonl file into Commit records.

    Source resolution:
      - a directory with a .git -> read `git log`
      - a .jsonl file (or a directory containing commits.jsonl) -> parse it
    """
    errors: list[dict[str, str]] = []
    raw: list[dict] = []
    source = ""

    jsonl = _resolve_jsonl(input_path)
    if input_path.is_dir() and is_git_repo(input_path):
        source = "git"
        try:
            raw = read_git_log(input_path, since=options.get("since"), max_count=options.get("max", 500))
        except RuntimeError as exc:
            errors.append({"error": str(exc)})
    elif jsonl is not None:
        source = "jsonl"
        for lineno, line in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append({"line": str(lineno), "error": str(exc)})
    else:
        errors.append({"error": f"{input_path} is not a git repo and has no commits.jsonl"})

    commits: list[Commit] = []
    for r in raw:
        subject = str(r.get("subject", ""))
        body = str(r.get("body", ""))
        parsed = parse_subject(subject, body)
        commits.append(
            Commit(
                hash=str(r.get("hash", "")),
                short_hash=str(r.get("short_hash", "") or str(r.get("hash", ""))[:8]),
                author=str(r.get("author", "")),
                date=str(r.get("date", "")),
                subject=subject,
                body=body,
                type=parsed["type"],
                scope=parsed["scope"],
                breaking=parsed["breaking"],
                conventional=parsed["conventional"],
                pr_number=parsed["pr_number"],
                metadata={"description": parsed["description"]},
            )
        )

    options["_errors"] = errors
    options["_source"] = source
    return commits


def _resolve_jsonl(input_path: Path) -> Path | None:
    if input_path.is_file() and input_path.suffix == ".jsonl":
        return input_path
    if input_path.is_dir():
        candidate = input_path / "commits.jsonl"
        if candidate.exists():
            return candidate
    return None
