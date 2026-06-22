from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_dockerfile.parse import discover_dockerfiles, parse_dockerfile
from tessera_dockerfile.schema import Instruction


def load_dockerfile_records(input_path: Path, options: dict[str, Any]) -> list[Instruction]:
    root = input_path if input_path.is_dir() else input_path.parent
    files = discover_dockerfiles(input_path if input_path.is_file() else root)
    instructions: list[Instruction] = []
    for f in files:
        rel = f.relative_to(root).as_posix() if f.is_relative_to(root) else f.name
        instructions.extend(parse_dockerfile(f, rel))
    options["_file_count"] = len(files)
    options["_files"] = [str(f) for f in files]
    options["_root"] = str(root)
    return instructions
