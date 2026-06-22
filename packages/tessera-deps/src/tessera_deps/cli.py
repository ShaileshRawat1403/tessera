from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_deps.pack import DepsPack

console = Console()
deps_app = typer.Typer(help="Audit dependency manifests for pinning, duplicates, and conflicts.")


@deps_app.command("audit")
def audit_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Project directory or a manifest file."),
    output: Path = typer.Option(Path("deps_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Inventory dependencies across manifests and flag pinning/duplicate issues."""
    ctx = RunContext(job_name="deps", output_dir=output)
    pack = DepsPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Deps Pack Created")
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
    summary.add_row("dependencies", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(deps_app, name="deps")
