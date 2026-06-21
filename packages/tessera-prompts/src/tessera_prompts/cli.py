from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_prompts.pack import PromptsPack

console = Console()
prompts_app = typer.Typer(help="Compile prompt collections into validated catalog assets.")


@prompts_app.command("compile")
def compile_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="Prompt directory or single prompt file."),
    output: Path = typer.Option(Path("prompt_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Compile a directory of prompt files into a canonical catalog plus reports."""
    ctx = RunContext(job_name="prompts", output_dir=output)
    pack = PromptsPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Prompt Pack Created")
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
    root_app.add_typer(prompts_app, name="prompts")
