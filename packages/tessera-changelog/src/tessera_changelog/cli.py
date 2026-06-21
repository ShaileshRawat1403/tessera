from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_changelog.pack import ChangelogPack

console = Console()
changelog_app = typer.Typer(help="Turn git history into a structured changelog and release notes.")


@changelog_app.command("build")
def build_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="A git repo, or a commits.jsonl file/dir."),
    output: Path = typer.Option(Path("changelog_pack"), "--output", "-o", help="Output directory."),
    since: str = typer.Option("", "--since", help="Only commits after this ref (e.g. the last tag)."),
    max: int = typer.Option(500, "--max", help="Maximum commits to read."),
) -> None:
    """Generate CHANGELOG.md, release notes, and reports from commit history."""
    ctx = RunContext(job_name="changelog", output_dir=output)
    options: dict = {"max": max}
    if since:
        options["since"] = since

    pack = ChangelogPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options=options)

    table = Table(title="Changelog Pack Created")
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
    summary.add_row("commits", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(changelog_app, name="changelog")
