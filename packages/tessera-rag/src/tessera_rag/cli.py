from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_rag.pack import RagPack

console = Console()
rag_app = typer.Typer(help="Compile a corpus + queries into a validated retrieval eval dataset.")


@rag_app.command("compile")
def compile_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="Directory with a corpus/ folder and a queries.jsonl/.yaml file."),
    output: Path = typer.Option(Path("rag_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Build a canonical retrieval eval dataset with verified document references."""
    ctx = RunContext(job_name="rag", output_dir=output)
    pack = RagPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="RAG Pack Created")
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
    root_app.add_typer(rag_app, name="rag")
