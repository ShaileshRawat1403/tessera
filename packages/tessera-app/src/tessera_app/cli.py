from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tessera_app.dashboard import build_dashboard
from tessera_app.detect import detect_packs
from tessera_app.orchestrator import run_project

console = Console()
app = typer.Typer(help="Run the whole Tessera hub over a project and build a dashboard.")


@app.command("detect")
def detect_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, help="Project directory."),
) -> None:
    """Show which packs apply to a project, without running them."""
    detections = detect_packs(input)
    table = Table(title="Applicable Packs")
    table.add_column("Pack")
    table.add_column("Why")
    for d in detections:
        table.add_row(d.pack, d.reason)
    if not detections:
        console.print("[yellow]No packs detected for this project.[/yellow]")
        return
    console.print(table)


@app.command("run")
def run_cmd(
    input: Path = typer.Option(Path("."), "--input", "-i", exists=True, help="Project directory."),
    output: Path = typer.Option(Path("tessera_run"), "--output", "-o", help="Output directory."),
    only: str = typer.Option("", "--only", help="Comma-separated pack names to limit the run."),
    dashboard: bool = typer.Option(True, "--dashboard/--no-dashboard", help="Build an HTML dashboard after the run."),
) -> None:
    """Detect applicable packs, run them, and (by default) build a dashboard."""
    only_list = [s.strip() for s in only.split(",") if s.strip()] or None
    results = run_project(input, output, only=only_list)

    table = Table(title="Tessera Run")
    table.add_column("Pack")
    table.add_column("Status")
    table.add_column("Records", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("Errors", justify="right")
    for r in results:
        status = "ok" if r.ok else "FAILED"
        table.add_row(r.pack, status, str(r.record_count), str(r.finding_count), str(r.error_count))
    console.print(table)

    if not results:
        console.print("[yellow]No packs were applicable.[/yellow]")
        return

    if dashboard:
        html_path = build_dashboard(output)
        console.print(f"[green]Dashboard:[/green] {html_path}")


@app.command("dashboard")
def dashboard_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, help="A tessera run output directory (contains run_manifest.json)."),
    output: Path = typer.Option(None, "--output", "-o", help="HTML path (default: <input>/index.html)."),
) -> None:
    """Build (or rebuild) the HTML dashboard from a run output directory."""
    html_path = build_dashboard(input, output)
    console.print(f"[green]Dashboard:[/green] {html_path}")


def register(root_app: typer.Typer) -> None:
    # tessera-app contributes top-level commands rather than a subgroup.
    root_app.command("run")(run_cmd)
    root_app.command("detect")(detect_cmd)
    root_app.command("dashboard")(dashboard_cmd)
