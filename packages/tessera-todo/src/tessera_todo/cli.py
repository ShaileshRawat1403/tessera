from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_todo.pack import TodoPack

console = Console()
todo_app = typer.Typer(help="Scan source for TODO/FIXME-style markers into a triaged backlog.")


@todo_app.command("scan")
def scan_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Project directory."),
    output: Path = typer.Option(Path("todo_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Collect code markers (TODO/FIXME/HACK/...) into a prioritized backlog."""
    ctx = RunContext(job_name="todo", output_dir=output)
    pack = TodoPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Todo Pack Created")
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
    summary.add_row("markers", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(todo_app, name="todo")
