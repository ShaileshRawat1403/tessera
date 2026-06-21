from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable

import typer

PluginRegister = Callable[[typer.Typer], None]


def load_cli_plugins(app: typer.Typer) -> list[str]:
    loaded: list[str] = []
    for ep in entry_points(group="systemsdk.commands"):
        register = ep.load()
        register(app)
        loaded.append(ep.name)
    return loaded
