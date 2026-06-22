from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_glossary.pack import GlossaryPack

console = Console()
glossary_app = typer.Typer(help="Extract a project's vocabulary and flag terminology drift.")


@glossary_app.command("build")
def build_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Project directory."),
    output: Path = typer.Option(Path("glossary_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Build a glossary of domain terms and report inconsistent spellings of a concept."""
    ctx = RunContext(job_name="glossary", output_dir=output)
    pack = GlossaryPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Glossary Pack Created")
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
    summary.add_row("terms", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(glossary_app, name="glossary")
