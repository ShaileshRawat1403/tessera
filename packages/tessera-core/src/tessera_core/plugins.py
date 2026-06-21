from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable

import typer

from tessera_core.jobpack import JobPack

PluginRegister = Callable[[typer.Typer], None]


def load_cli_plugins(app: typer.Typer) -> list[str]:
    """Load entry-point group ``tessera.commands`` into a Typer app."""
    loaded: list[str] = []
    for ep in entry_points(group="tessera.commands"):
        register = ep.load()
        register(app)
        loaded.append(ep.name)
    return loaded


def load_jobpacks() -> dict[str, JobPack]:
    """Load entry-point group ``tessera.jobpacks`` and instantiate each pack."""
    packs: dict[str, JobPack] = {}
    for ep in entry_points(group="tessera.jobpacks"):
        factory = ep.load()
        pack = factory()
        if not isinstance(pack, JobPack):
            raise TypeError(f"{ep.name} is not a JobPack (got {type(pack).__name__})")
        packs[pack.name] = pack
    return packs
