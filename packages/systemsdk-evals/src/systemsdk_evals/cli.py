from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from systemsdk_core.models import RunContext

from systemsdk_evals.pack import EvalsPack

console = Console()
evals_app = typer.Typer(help="Compile messy data into eval-ready assets.")


@evals_app.command("compile")
def compile_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="Input CSV path."),
    task: str = typer.Option(..., "--task", help="Task type, for example customer_support, rag_qa, classification."),
    output: Path = typer.Option(Path("eval_pack"), "--output", "-o", help="Output directory."),
    input_column: str | None = typer.Option(None, "--input-column", help="Override input/question column."),
    expected_column: str | None = typer.Option(None, "--expected-column", help="Override expected/golden-answer column."),
    context_column: str | None = typer.Option(None, "--context-column", help="Override context/source column."),
    enrich: bool = typer.Option(False, "--enrich", help="LLM-enriched rubric (not available in v0.1)."),
) -> None:
    """Create dataset, golden candidates, rubric, and quality reports from a CSV."""
    if enrich:
        console.print(
            "[yellow]LLM enrichment is not available in v0.1. Using deterministic rubric templates.[/yellow]"
        )

    ctx = RunContext(job_name="evals", output_dir=output)
    options = {
        "task_type": task,
        "input_column": input_column,
        "expected_column": expected_column,
        "context_column": context_column,
    }

    pack = EvalsPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options=options)

    table = Table(title="Eval Pack Created")
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
    root_app.add_typer(evals_app, name="evals")
