from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_config.pack import ConfigPack

console = Console()
config_app = typer.Typer(help="Inventory config keys, check for leaked secrets, and report drift.")


@config_app.command("audit")
def audit_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Project directory."),
    output: Path = typer.Option(Path("config_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Scan env files and code for config keys; redact secrets and report drift."""
    ctx = RunContext(job_name="config", output_dir=output)
    pack = ConfigPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Config Pack Created")
    table.add_column("Artifact")
    table.add_column("Path")
    table.add_column("Kind")
    for art in artifacts:
        table.add_row(art.name, str(art.path), art.kind)
    console.print(table)

    summary = Table(title="Run Summary")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("run_id", ctx.run_id)
    summary.add_row("keys", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(config_app, name="config")
