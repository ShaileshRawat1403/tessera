from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_repo.scanner import build_map, scan_repo
from tessera_repo.schema import RepoFile


def load_repo_records(input_path: Path, options: dict[str, Any]) -> list[RepoFile]:
    """Scan the repo into RepoFile records; stash manifests/signals/map in options."""
    root = input_path if input_path.is_dir() else input_path.parent
    files, manifests, signals = scan_repo(root)
    repo_map = build_map(root, files, manifests, signals)

    options["_manifests"] = manifests
    options["_signals"] = signals
    options["_map"] = repo_map
    options["_root"] = str(root)
    return files
