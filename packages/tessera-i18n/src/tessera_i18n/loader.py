from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tessera_i18n.schema import LocaleFile

_IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
_SKIP_NAMES = {"package.json", "package-lock.json", "tsconfig.json", "composer.json",
               "manifest.json", "babel.config.json", "jsconfig.json"}


def flatten(obj: Any, prefix: str = "") -> dict[str, str]:
    """Flatten a nested locale dict into dot-joined string keys."""
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(obj, list):
        # rare in locale files; index the entries
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = "" if obj is None else str(obj)
    return out


def discover_locale_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*.json")):
        if any(part in _IGNORE_DIRS for part in p.relative_to(root).parts):
            continue
        if p.name.lower() in _SKIP_NAMES:
            continue
        out.append(p)
    return out


def _locale_name(path: Path) -> str:
    stem = path.stem
    # e.g. messages.en -> en ; en -> en
    if "." in stem:
        return stem.rsplit(".", 1)[-1]
    return stem


def load_i18n_records(input_path: Path, options: dict[str, Any]) -> list[LocaleFile]:
    root = input_path if input_path.is_dir() else input_path.parent
    files = discover_locale_files(input_path if input_path.is_file() else root)

    parsed: list[tuple[str, str, dict[str, str]]] = []  # (locale, rel, flat)
    parse_errors: list[dict[str, str]] = []
    for f in files:
        rel = f.relative_to(root).as_posix() if f.is_relative_to(root) else f.name
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            parse_errors.append({"path": rel, "error": str(exc)})
            continue
        if not isinstance(data, dict):
            continue
        parsed.append((_locale_name(f), rel, flatten(data)))

    options["_parse_errors"] = parse_errors

    if not parsed:
        options["_reference"] = ""
        return []

    # reference: prefer "en", else the locale with the most keys
    ref_idx = 0
    en = [i for i, (loc, _, _) in enumerate(parsed) if loc.lower() in ("en", "en-us", "en_us")]
    if en:
        ref_idx = en[0]
    else:
        ref_idx = max(range(len(parsed)), key=lambda i: len(parsed[i][2]))
    ref_locale, _ref_rel, ref_flat = parsed[ref_idx]
    ref_keys = set(ref_flat.keys())
    options["_reference"] = ref_locale

    records: list[LocaleFile] = []
    for i, (loc, rel, flat) in enumerate(parsed):
        keys = set(flat.keys())
        missing = sorted(ref_keys - keys)
        extra = sorted(keys - ref_keys)
        empty = sorted(k for k, v in flat.items() if v == "")
        coverage = 1.0 if not ref_keys else (len(ref_keys & keys) / len(ref_keys))
        records.append(
            LocaleFile(
                locale=loc, path=rel, is_reference=(i == ref_idx),
                key_count=len(keys), coverage=round(coverage, 4),
                missing_keys=missing, extra_keys=extra, empty_keys=empty,
            )
        )
    return records
