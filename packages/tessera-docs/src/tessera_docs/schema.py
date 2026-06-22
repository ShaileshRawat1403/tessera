from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocSymbol(BaseModel):
    """A documentable Python symbol. Serialized to ``symbols.jsonl``."""

    path: str            # repo-relative source file, POSIX
    qualname: str        # dotted name within the module (module-level = "")
    kind: str            # module / class / function / method
    name: str
    lineno: int = 0
    is_public: bool = True
    has_docstring: bool = False
    docstring_len: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
