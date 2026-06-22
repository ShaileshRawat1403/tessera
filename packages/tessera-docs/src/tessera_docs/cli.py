from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_docs.pack import DocsPack

console = Console()
docs_app = typer.Typer(help="Measure Python docstring coverage for public symbols.")


@docs_app.command("coverage")
def coverage_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Project directory."),
    output: Path = typer.Option(Path("docs_pack"), "--output", "-o", help="Output directory."),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include test files in the scan."),
) -> None:
    """Scan Python source and report docstring coverage for public symbols."""
    ctx = RunContext(job_name="docs", output_dir=output)
    pack = DocsPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={"include_tests": include_tests})

    table = Table(title="Docs Pack Created")
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
    summary.add_row("symbols", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(docs_app, name="docs")
