from collections.abc import Sequence
from sqlite3 import Connection, Row
from typing import Any, Generic, TypeVar

from tagumori.models import RowModel

T = TypeVar("T", bound=RowModel)


def _placeholders(count: int, placeholder: str = "?"):
    return ",".join(placeholder for _ in range(count))


class BaseCRUD(Generic[T]):
    """A Baseclass with implementations of the most common shared logic."""

    def __init__(self, table: str, unique_col: str, model: type[T]):
        self.table = table
        self.unique_col = unique_col
        self.model = model

    def _one(self, item: Row | None) -> T | None:
        """Utility for transforming one Row to output model"""
        if item is None:
            return None

        return self.model.from_row(item)

    def _one_or_raise(self, item: Row | None) -> T:
        result = self._one(item)
        if result is None:
            raise RuntimeError(f"Expected a row from {self.table}, got None")
        return result

    def _many(self, items: Sequence[Row]) -> list[T]:
        """Utility for transforming many Rows to output model"""
        return [x for x in map(self._one, items) if x is not None]

    def get_all(self, conn: Connection) -> list[T]:
        return self._many(
            conn.execute(f"SELECT * FROM {self.table}").fetchall(),
        )

    def get(self, conn: Connection, id: int) -> T | None:
        return self._one(
            conn.execute(f"SELECT * FROM {self.table} WHERE id = ?", (id,)).fetchone()
        )

    def get_many(self, conn: Connection, ids: Sequence[int]) -> list[T]:
        phs = _placeholders(len(ids))

        return self._many(
            conn.execute(
                f"SELECT * FROM {self.table} WHERE id IN ({phs})", ids
            ).fetchall()
        )

    def get_by_unique_col(self, conn: Connection, value: Any) -> T | None:
        # TODO: should change to a generic type var here instead of Any

        return self._one(
            conn.execute(
                f"SELECT * FROM {self.table} WHERE {self.unique_col} = ?", (value,)
            ).fetchone()
        )

    def get_many_by_unique_col(
        self, conn: Connection, values: Sequence[Any]
    ) -> list[T]:
        phs = _placeholders(len(values))
        return self._many(
            conn.execute(
                f"SELECT * FROM {self.table} WHERE {self.unique_col} IN ({phs})", values
            ).fetchall()
        )

    def delete(self, conn: Connection, id: int) -> None:
        conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (id,))
