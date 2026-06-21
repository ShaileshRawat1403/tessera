from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from systemsdk_core import __version__
from systemsdk_core.plugins import load_cli_plugins
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
    """Show installed command plugins."""
    table = Table(title="SystemSDK Plugins")
    table.add_column("Plugin")
    for name in load_cli_plugins(typer.Typer()):
        table.add_row(name)
    console.print(table)


def main() -> None:
    load_cli_plugins(app)
    app()
