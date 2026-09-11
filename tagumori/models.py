import json
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Row
from typing import Self

from tagumori.query.ast import Expr


class RowModel:
    __slots__ = ()

    @classmethod
    def from_row(cls, row: Row) -> Self:
        return cls(**row)


@dataclass(frozen=True, slots=True)
class File(RowModel):
    id: int
    path: Path
    inode: int | None
    device: int | None

    @classmethod
    def from_row(cls, row) -> "File":
        data = {
            **row,
            "path": Path(row["path"]),
        }
        return cls(**data)


@dataclass(frozen=True, slots=True)
class Tag(RowModel):
    id: int
    name: str
    category: str | None


@dataclass(frozen=True, slots=True)
class Query(RowModel):
    id: int
    name: str
    select_tags: tuple[str, ...]  # json in db
    exclude_tags: tuple[str, ...]  # json in db
    pattern: str
    ignore_case: bool  # integer in db
    invert_match: bool
    ignore_tag_case: bool

    @classmethod
    def from_row(cls, row) -> "Query":
        return cls(
            id=row["id"],
            name=row["name"],
            select_tags=tuple(json.loads(row["select_tags"] or "[]")),
            exclude_tags=tuple(json.loads(row["exclude_tags"] or "[]")),
            pattern=row["pattern"] or r".*",
            ignore_case=bool(row["ignore_case"]),
            invert_match=bool(row["invert_match"]),
            ignore_tag_case=bool(row["ignore_tag_case"]),
        )


@dataclass
class TaggedFile:
    file: File
    tags: Expr | None = None
