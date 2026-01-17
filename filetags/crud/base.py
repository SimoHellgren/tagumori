from collections.abc import Sequence
from sqlite3 import Connection, Row
from typing import Any


def _placeholders(count: int, placeholder: str = "?"):
    return ",".join(placeholder for _ in range(count))


class BaseCRUD:
    """A Baseclass with implementations of the most common shared logic."""

    def __init__(self, table: str, unique_col: str):
        self.table = table
        self.unique_col = unique_col

    def get_all(self, conn: Connection) -> list[Row]:
        return conn.execute(f"SELECT * FROM {self.table}").fetchall()

    def get(self, conn: Connection, id: int) -> Row:
        return conn.execute(
            f"SELECT * FROM {self.table} WHERE id = ?", (id,)
        ).fetchone()

    def get_many(self, conn: Connection, ids: Sequence[int]) -> list[Row]:
        phs = _placeholders(len(ids))

        return conn.execute(
            f"SELECT * FROM {self.table} WHERE id IN ({phs})", ids
        ).fetchall()

    def get_by_unique_col(self, conn: Connection, value: Any) -> Row:
        # TODO: should change to a generic type var here instead of Any

        return conn.execute(
            f"SELECT * FROM {self.table} WHERE {self.unique_col} = ?", (value,)
        ).fetchone()

    def get_many_by_unique_col(
        self, conn: Connection, values: Sequence[Any]
    ) -> list[Row]:
        phs = _placeholders(len(values))
        return conn.execute(
            f"SELECT * FROM {self.table} WHERE {self.unique_col} IN ({phs})", values
        ).fetchall()

    def delete(self, conn: Connection, id: int) -> None:
        conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (id,))
