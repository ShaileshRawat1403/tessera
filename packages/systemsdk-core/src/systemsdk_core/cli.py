from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from systemsdk_core import __version__
from systemsdk_core.plugins import load_cli_plugins, load_jobpacks
from systemsdk_core.workspace import DEFAULT_HOME, ensure_workspace

console = Console()
app = typer.Typer(help="SystemSDK: reusable workflow tools for AI and engineering jobs.")


@app.callback()
def callback() -> None:
    """Reusable workflow SDK runtime."""


@app.command()
def init(home: Path = typer.Option(DEFAULT_HOME, help="Workspace directory.")) -> None:
    """Create the local SystemSDK workspace."""
    path = ensure_workspace(home)
    console.print(f"Workspace ready: {path}")


@app.command()
def version() -> None:
    """Show installed core version."""
    console.print(__version__)


@app.command("plugins")
def plugins_cmd() -> None:
    """Show installed CLI command plugins and job packs."""
    commands_table = Table(title="CLI Command Plugins (systemsdk.commands)")
    commands_table.add_column("Name")
    probe = typer.Typer()
    for name in load_cli_plugins(probe):
        commands_table.add_row(name)
    console.print(commands_table)

    packs_table = Table(title="Job Packs (systemsdk.jobpacks)")
    packs_table.add_column("Name")
    packs_table.add_column("Version")
    packs_table.add_column("Class")
    for name, pack in load_jobpacks().items():
        packs_table.add_row(name, pack.version, type(pack).__name__)
    console.print(packs_table)


def main() -> None:
    load_cli_plugins(app)
    app()
