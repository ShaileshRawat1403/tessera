from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_tests.scan import discover_test_files, extract_tests
from tessera_tests.schema import TestCase


def load_test_records(input_path: Path, options: dict[str, Any]) -> list[TestCase]:
    root = input_path if input_path.is_dir() else input_path.parent
    cases: list[TestCase] = []
    parse_errors: list[str] = []
    files = discover_test_files(root)
    for f in files:
        found, err = extract_tests(root, f)
        cases.extend(found)
        if err:
            parse_errors.append(err)
    options["_parse_errors"] = parse_errors
    options["_file_count"] = len(files)
    options["_root"] = str(root)
    return cases
