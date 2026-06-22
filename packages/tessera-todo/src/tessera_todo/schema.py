from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TodoItem(BaseModel):
    """A code marker (TODO/FIXME/...). Serialized to ``todos.jsonl``."""

    marker: str        # TODO / FIXME / HACK / XXX / BUG / NOTE / OPTIMIZE / REFACTOR / DEPRECATED
    priority: str = "normal"  # high / normal / low
    owner: str = ""    # from TODO(owner): ...
    text: str = ""
    file: str = ""
    lineno: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
