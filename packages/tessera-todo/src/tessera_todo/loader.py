from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_todo.scan import scan_todos
from tessera_todo.schema import TodoItem


def load_todo_records(input_path: Path, options: dict[str, Any]) -> list[TodoItem]:
    root = input_path if input_path.is_dir() else input_path.parent
    items, files = scan_todos(root)
    options["_file_count"] = files
    options["_root"] = str(root)
    return items
