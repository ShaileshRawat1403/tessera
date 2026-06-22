from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_dockerfile.pack import DockerfilePack

console = Console()
dockerfile_app = typer.Typer(help="Lint Dockerfiles for image hygiene and security.")


@dockerfile_app.command("lint")
def lint_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="A Dockerfile or a directory containing one."),
    output: Path = typer.Option(Path("dockerfile_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Parse and lint Dockerfiles; emit an instruction inventory and findings."""
    ctx = RunContext(job_name="dockerfile", output_dir=output)
    pack = DockerfilePack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="Dockerfile Pack Created")
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
    summary.add_row("instructions", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(dockerfile_app, name="dockerfile")
