from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_repo.pack import RepoPack

console = Console()
repo_app = typer.Typer(help="Map a repository into a validated structural artifact.")


@repo_app.command("map")
def map_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Repository root directory."),
    output: Path = typer.Option(Path("repo_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Scan a repository into a file inventory, structural map, and reports."""
    ctx = RunContext(job_name="repo", output_dir=output)
    pack = RepoPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Repo Pack Created")
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
    summary.add_row("files", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(repo_app, name="repo")
