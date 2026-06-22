from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_openapi.pack import OpenApiPack

console = Console()
openapi_app = typer.Typer(help="Lint an OpenAPI/Swagger spec into an endpoint catalog + findings.")


@openapi_app.command("lint")
def lint_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="A spec file or a directory containing one."),
    output: Path = typer.Option(Path("openapi_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Parse and lint an OpenAPI/Swagger spec; emit an endpoint catalog and reports."""
    ctx = RunContext(job_name="openapi", output_dir=output)
    pack = OpenApiPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="OpenAPI Pack Created")
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
    summary.add_row("endpoints", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(openapi_app, name="openapi")
