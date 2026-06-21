from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from systemsdk_evals.compiler import write_eval_pack

console = Console()
evals_app = typer.Typer(help="Compile messy data into eval-ready assets.")


@evals_app.command("compile")
def compile_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="Input CSV path."),
    task: str = typer.Option(..., "--task", help="Task type, for example customer_support, rag_qa, extraction."),
    output: Path = typer.Option(Path("eval_pack"), "--output", "-o", help="Output directory."),
    input_column: str | None = typer.Option(None, help="Override input/question column."),
    expected_column: str | None = typer.Option(None, help="Override expected/golden-answer column."),
    context_column: str | None = typer.Option(None, help="Override context/source column."),
) -> None:
    """Create dataset, golden candidates, rubric, and quality reports from a CSV."""
    result = write_eval_pack(
        input_path=input,
        output_dir=output,
        task_type=task,
        input_column=input_column,
        expected_column=expected_column,
        context_column=context_column,
    )
    table = Table(title="Eval Pack Created")
    table.add_column("Item")
    table.add_column("Value")
    for key, value in result.items():
        table.add_row(str(key), str(value))
    console.print(table)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(evals_app, name="evals")
