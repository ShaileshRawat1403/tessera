from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_sql.pack import SqlPack

console = Console()
sql_app = typer.Typer(help="Lint SQL files/migrations into a statement and table catalog.")


@sql_app.command("lint")
def lint_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="A .sql file or a directory of them."),
    output: Path = typer.Option(Path("sql_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Parse and lint SQL; emit statement/table catalogs and findings."""
    ctx = RunContext(job_name="sql", output_dir=output)
    pack = SqlPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="SQL Pack Created")
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
    summary.add_row("statements", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(sql_app, name="sql")
