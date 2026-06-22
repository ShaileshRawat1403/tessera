from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_license.pack import LicensePack

console = Console()
license_app = typer.Typer(help="Detect and classify project licenses (offline).")


@license_app.command("audit")
def audit_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Project directory."),
    output: Path = typer.Option(Path("license_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Detect the license from LICENSE files and manifests; flag copyleft/missing."""
    ctx = RunContext(job_name="license", output_dir=output)
    pack = LicensePack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="License Pack Created")
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
    summary.add_row("declarations", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(license_app, name="license")
