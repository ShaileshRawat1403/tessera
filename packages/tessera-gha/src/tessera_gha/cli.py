from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_gha.pack import GhaPack

console = Console()
gha_app = typer.Typer(help="Lint GitHub Actions workflows for security and hygiene.")


@gha_app.command("lint")
def lint_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Repo root, a workflows dir, or a workflow file."),
    output: Path = typer.Option(Path("gha_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Parse .github/workflows and flag unpinned actions, injection risks, and more."""
    ctx = RunContext(job_name="gha", output_dir=output)
    pack = GhaPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="GHA Pack Created")
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
    summary.add_row("steps", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(gha_app, name="gha")
