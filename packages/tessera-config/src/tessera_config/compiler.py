from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_config.loader import load_config_records
from tessera_config.schema import ConfigKey
from tessera_config.validator import validate_config_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[ConfigKey]:
    return load_config_records(input_path, options)


def validate_records(keys: list[ConfigKey], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_config_records(keys, options)


def write_artifacts(keys: list[ConfigKey], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(keys, options)

    inventory = ctx.output_dir / "config_inventory.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    drift_md = ctx.output_dir / "drift_report.md"

    write_jsonl(inventory, [k.model_dump() for k in keys])
    write_markdown(index_md, _render_index(keys, options))
    write_markdown(validation_md, _render_validation(keys, findings))
    write_markdown(coverage_md, _render_coverage(keys))
    write_markdown(drift_md, _render_drift(keys))

    return [
        Artifact(name="config_inventory.jsonl", path=inventory, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="drift_report.md", path=drift_md, kind="markdown"),
    ]


def _yn(b: bool) -> str:
    return "yes" if b else "-"


def _render_index(keys: list[ConfigKey], options: dict[str, Any]) -> str:
    lines = ["# Config Inventory", ""]
    lines.append(f"- Keys: {len(keys)}")
    lines.append(f"- Real env files: {len(options.get('_real_files', []))}")
    lines.append(f"- Example files: {len(options.get('_example_files', []))}")
    lines.append("")
    if not keys:
        lines.append("_No config keys found._")
        return "\n".join(lines) + "\n"
    lines.append("| Key | env | example | code | secret | value |")
    lines.append("|---|:--:|:--:|:--:|:--:|---|")
    for k in keys:
        lines.append(
            f"| `{k.name}` | {_yn(k.in_env)} | {_yn(k.in_example)} | {_yn(k.in_code)} "
            f"| {_yn(k.is_secret)} | {k.value_preview or ''} |"
        )
    return "\n".join(lines) + "\n"


def _render_validation(keys: list[ConfigKey], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Keys: {len(keys)}")
    lines.append(f"- Findings: {len(findings)}")
    lines.append("")
    by_sev = Counter(f.severity for f in findings)
    lines.append("## Severity Breakdown")
    lines.append("")
    for sev in ("error", "warning", "info"):
        lines.append(f"- {sev}: {by_sev.get(sev, 0)}")
    lines.append("")
    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings[:200]:
            key = f.metadata.get("key", "") if f.metadata else ""
            who = f" `{key}`" if key else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{who}: {f.message}")
    return "\n".join(lines)


def _render_coverage(keys: list[ConfigKey]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Keys: {len(keys)}")
    if not keys:
        return "\n".join(lines) + "\n"
    documented = sum(1 for k in keys if k.in_example)
    used = sum(1 for k in keys if k.in_code)
    secrets = sum(1 for k in keys if k.is_secret)
    lines.append(f"- Documented in an example: {documented} ({100*documented/len(keys):.0f}%)")
    lines.append(f"- Referenced in code: {used} ({100*used/len(keys):.0f}%)")
    lines.append(f"- Secret-named keys: {secrets}")
    return "\n".join(lines) + "\n"


def _render_drift(keys: list[ConfigKey]) -> str:
    missing = [k.name for k in keys if k.in_code and not k.in_example]
    undocumented = [k.name for k in keys if k.in_env and not k.in_example]
    unused = [k.name for k in keys if k.in_example and not k.in_code and not k.in_env]

    lines = ["# Config Drift Report", ""]
    lines.append("How the declared, set, and used config sets diverge.")
    lines.append("")

    def block(title: str, items: list[str], hint: str) -> None:
        lines.append(f"## {title} ({len(items)})")
        lines.append("")
        lines.append(hint)
        lines.append("")
        if items:
            for name in items:
                lines.append(f"- `{name}`")
        else:
            lines.append("_None._")
        lines.append("")

    block("Used in code but undocumented", missing,
          "Add these to a .env.example so others know they are required.")
    block("Set in .env but undocumented", undocumented,
          "These exist in a real .env but no example documents them.")
    block("Documented but unused", unused,
          "These appear in an example but are never read or set; consider removing.")
    return "\n".join(lines)
