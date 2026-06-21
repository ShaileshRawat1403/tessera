from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_HOME = Path.home() / ".tessera"


def ensure_workspace(home: Path = DEFAULT_HOME) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    (home / "projects").mkdir(exist_ok=True)
    (home / "runs").mkdir(exist_ok=True)
    return home


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
