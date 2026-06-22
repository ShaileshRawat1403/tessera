from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SqlStatement(BaseModel):
    """One SQL statement. Serialized to ``statements.jsonl``."""

    kind: str          # create_table / create_index / alter / drop / select / insert / update / delete / other
    target: str = ""   # table/index name when determinable
    file: str = ""
    lineno: int = 0
    preview: str = ""  # first ~100 chars, comments stripped
    flags: dict[str, Any] = Field(default_factory=dict)  # parser observations (has_where, if_exists, select_star, ...)


class SqlTable(BaseModel):
    """A table declared by a CREATE TABLE. Serialized to ``tables.jsonl``."""

    name: str
    columns: list[str] = Field(default_factory=list)
    has_primary_key: bool = False
    file: str = ""
    lineno: int = 0
