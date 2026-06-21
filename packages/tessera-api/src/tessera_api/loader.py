from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_api.curl import parse_curl, split_curl_commands
from tessera_api.schema import ApiRequest


def discover_curl_files(root: Path) -> list[Path]:
    """Find curl-bearing files: ``*.curl`` and ``*.sh`` (or a single file)."""
    if root.is_file():
        return [root]
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in (".curl", ".sh"):
            found.append(path)
    return found


def load_api_records(input_path: Path, options: dict[str, Any]) -> list[ApiRequest]:
    """Parse every curl command in the input into redacted ApiRequest records."""
    files = discover_curl_files(input_path)
    records: list[ApiRequest] = []
    parse_errors: list[dict[str, str]] = []

    seq = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        for cmd in split_curl_commands(text):
            seq += 1
            rid = f"{path.stem}_{seq}"
            try:
                rec = parse_curl(cmd, rid)
                rec.metadata["source_file"] = str(path)
                records.append(rec)
            except ValueError as exc:
                parse_errors.append({"source_file": str(path), "error": str(exc), "preview": cmd[:80]})

    options["_parse_errors"] = parse_errors
    options["_input_path"] = str(input_path)
    return records
