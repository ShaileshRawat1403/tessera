from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_api.pack import ApiPack

console = Console()
api_app = typer.Typer(help="Parse curl/HTTP traces into a validated, redacted API surface map.")


@api_app.command("compile")
def compile_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="A .curl/.sh file or a directory of them."),
    output: Path = typer.Option(Path("api_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Parse curl commands into canonical, secret-redacted API request records."""
    ctx = RunContext(job_name="api", output_dir=output)
    pack = ApiPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="API Pack Created")
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
    summary.add_row("records", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(api_app, name="api")
