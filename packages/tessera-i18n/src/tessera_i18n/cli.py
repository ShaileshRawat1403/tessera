from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_core.models import RunContext

from tessera_i18n.pack import I18nPack

console = Console()
i18n_app = typer.Typer(help="Check translation-key coverage across locale files.")


@i18n_app.command("check")
def check_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, readable=True, help="Directory of locale JSON files."),
    output: Path = typer.Option(Path("i18n_pack"), "--output", "-o", help="Output directory."),
) -> None:
    """Compare locales against a reference and report missing/extra/empty keys."""
    ctx = RunContext(job_name="i18n", output_dir=output)
    pack = I18nPack()
    artifacts = pack.run(input_path=input, ctx=ctx, options={})

    table = Table(title="i18n Pack Created")
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
    summary.add_row("locales", str(ctx.metadata.get("record_count", 0)))
    summary.add_row("findings", str(ctx.metadata.get("finding_count", 0)))
    console.print(summary)


def register(root_app: typer.Typer) -> None:
    root_app.add_typer(i18n_app, name="i18n")
