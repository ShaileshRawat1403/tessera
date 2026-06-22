from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_links.pack import LinksPack

console = Console()
links_app = typer.Typer(help="Check markdown links: broken file links, dead anchors, orphan docs.")


@links_app.command("check")
def check_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Project or docs directory."),
    output: Path = typer.Option(Path("links_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Inventory markdown links and flag broken internal links, anchors, and orphans."""
    ctx = RunContext(job_name="links", output_dir=output)
    pack = LinksPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Links Pack Created")
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
    summary.add_row("links", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(links_app, name="links")
