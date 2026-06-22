from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConfigKey(BaseModel):
    """A configuration key aggregated across env files and code. Serialized to
    ``config_inventory.jsonl``. Secret values are never stored raw; only a
    masked preview is kept."""

    name: str
    in_env: bool = False          # present (with a value) in a real .env file
    in_example: bool = False      # documented in .env.example / .sample / .template
    in_code: bool = False         # referenced in source (os.getenv / process.env / ...)
    is_secret: bool = False       # name matches a secret pattern
    value_preview: str = ""       # masked if secret; "(set)" / "" otherwise
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
