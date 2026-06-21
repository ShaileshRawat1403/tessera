from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable

import typer

from systemsdk_core.jobpack import JobPack

PluginRegister = Callable[[typer.Typer], None]


def load_cli_plugins(app: typer.Typer) -> list[str]:
    """Load entry-point group ``systemsdk.commands`` into a Typer app."""
    loaded: list[str] = []
    for ep in entry_points(group="systemsdk.commands"):
        register = ep.load()
        register(app)
        loaded.append(ep.name)
    return loaded


def load_jobpacks() -> dict[str, JobPack]:
    """Load entry-point group ``systemsdk.jobpacks`` and instantiate each pack."""
    packs: dict[str, JobPack] = {}
    for ep in entry_points(group="systemsdk.jobpacks"):
        factory = ep.load()
        pack = factory()
        if not isinstance(pack, JobPack):
            raise TypeError(f"{ep.name} is not a JobPack (got {type(pack).__name__})")
        packs[pack.name] = pack
    return packs
