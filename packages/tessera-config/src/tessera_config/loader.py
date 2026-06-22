from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_config.envparse import parse_env
from tessera_config.redact import is_secret_name, mask
from tessera_config.scan import find_code_references, find_env_files
from tessera_config.schema import ConfigKey


def load_config_records(input_path: Path, options: dict[str, Any]) -> list[ConfigKey]:
    """Aggregate config keys across real env files, example files, and code.

    Secret values are masked here, before any ConfigKey is built, so no raw
    secret ever reaches a record or an artifact.
    """
    root = input_path if input_path.is_dir() else input_path.parent
    real_files, example_files = find_env_files(root)
    code_refs = find_code_references(root)

    # key -> aggregation state
    keys: dict[str, dict[str, Any]] = {}

    def ensure(name: str) -> dict[str, Any]:
        return keys.setdefault(name, {"sources": set(), "value": "", "in_env": False,
                                      "in_example": False, "in_code": False})

    for f in real_files:
        rel = f.relative_to(root).as_posix()
        for k, v in parse_env(f).items():
            st = ensure(k)
            st["in_env"] = True
            st["sources"].add(rel)
            if v and not st["value"]:
                st["value"] = v

    for f in example_files:
        rel = f.relative_to(root).as_posix()
        for k in parse_env(f).keys():
            st = ensure(k)
            st["in_example"] = True
            st["sources"].add(rel)

    for name, files in code_refs.items():
        st = ensure(name)
        st["in_code"] = True
        for fl in files:
            st["sources"].add(fl)

    records: list[ConfigKey] = []
    for name in sorted(keys):
        st = keys[name]
        secret = is_secret_name(name)
        value = st["value"]
        if value:
            preview = mask(value) if secret else "(set)"
        else:
            preview = ""
        records.append(
            ConfigKey(
                name=name,
                in_env=st["in_env"],
                in_example=st["in_example"],
                in_code=st["in_code"],
                is_secret=secret,
                value_preview=preview,
                sources=sorted(st["sources"]),
            )
        )

    options["_real_files"] = [f.relative_to(root).as_posix() for f in real_files]
    options["_example_files"] = [f.relative_to(root).as_posix() for f in example_files]
    options["_root"] = str(root)
    return records
