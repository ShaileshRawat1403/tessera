from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from tessera_core.models import ValidationFinding

from tessera_dockerfile.schema import Instruction

_SECRET_KEY_RE = re.compile(r"(secret|token|password|passwd|api[_-]?key|access[_-]?key|private[_-]?key|credential)", re.IGNORECASE)


def _env_keys(arg: str) -> list[tuple[str, str]]:
    """Return (key, value) pairs from an ENV/ARG argument."""
    pairs: list[tuple[str, str]] = []
    if "=" in arg:
        for token in arg.split():
            if "=" in token:
                k, _, v = token.partition("=")
                pairs.append((k.strip(), v.strip()))
    else:
        parts = arg.split(None, 1)
        if len(parts) == 2:
            pairs.append((parts[0].strip(), parts[1].strip()))
    return pairs


def validate_dockerfile_records(instrs: list[Instruction], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not instrs:
        findings.append(ValidationFinding(severity="info", code="no_dockerfile",
                                          message="no Dockerfile found", field=None))
        return findings

    by_file: dict[str, list[Instruction]] = defaultdict(list)
    for ins in instrs:
        by_file[ins.file].append(ins)

    for file, items in by_file.items():
        stage_names: set[str] = set()
        for ins in items:
            if ins.instruction == "FROM":
                m = re.search(r"\bAS\s+([A-Za-z0-9_.-]+)\s*$", ins.argument, re.IGNORECASE)
                if m:
                    stage_names.add(m.group(1).lower())

        has_user = any(i.instruction == "USER" for i in items)
        has_healthcheck = any(i.instruction == "HEALTHCHECK" for i in items)

        def f(severity: str, code: str, message: str, lineno: int) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="dockerfile", metadata={"file": file, "lineno": lineno})

        for ins in items:
            loc = f"{file}:{ins.lineno}"
            if ins.instruction == "FROM":
                base = ins.argument.split()[0] if ins.argument else ""
                image = base.split(" AS ")[0].strip()
                name = image.split(":")[0].lower()
                tag = image.split(":")[1] if ":" in image else ""
                if name in stage_names or name == "scratch":
                    pass
                elif not tag:
                    findings.append(f("warning", "unpinned_base_image",
                                      f"{loc}: FROM {image} has no tag (defaults to :latest)", ins.lineno))
                elif tag == "latest":
                    findings.append(f("warning", "latest_tag",
                                      f"{loc}: FROM {image} uses the :latest tag", ins.lineno))

            if ins.instruction == "ADD":
                arg0 = ins.argument.split()[0] if ins.argument else ""
                if not arg0.startswith(("http://", "https://")) and not arg0.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2")):
                    findings.append(f("info", "add_instead_of_copy",
                                      f"{loc}: prefer COPY over ADD for local files", ins.lineno))

            if ins.instruction in ("ENV", "ARG"):
                for k, v in _env_keys(ins.argument):
                    if _SECRET_KEY_RE.search(k) and v:
                        findings.append(f("warning", "secret_in_image",
                                          f"{loc}: {ins.instruction} {k}=... bakes a secret into an image layer", ins.lineno))

        if not has_user:
            first_line = items[0].lineno if items else 0
            findings.append(f("warning", "runs_as_root", f"{file}: no USER instruction; container runs as root", first_line))
        if not has_healthcheck:
            first_line = items[0].lineno if items else 0
            findings.append(f("info", "missing_healthcheck", f"{file}: no HEALTHCHECK instruction", first_line))

    return findings
