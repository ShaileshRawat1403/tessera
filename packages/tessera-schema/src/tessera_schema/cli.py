from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_schema.pack import SchemaPack

console = Console()
schema_app = typer.Typer(help="Catalog and lint JSON Schema documents.")


@schema_app.command("lint")
def lint_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="A JSON Schema file or a directory of them."),
    output: Path = typer.Option(Path("schema_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Catalog JSON Schema documents and flag structural issues."""
    ctx = RunContext(job_name="schema", output_dir=output)
    pack = SchemaPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Schema Pack Created")
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
    summary.add_row("schemas", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(schema_app, name="schema")
