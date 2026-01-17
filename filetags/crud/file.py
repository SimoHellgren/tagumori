from pathlib import Path
from sqlite3 import Connection, Row
from typing import Sequence

from filetags.crud.base import BaseCRUD, _placeholders


class FileCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(table="file", unique_col="path")

    def get_by_path(self, conn: Connection, path: Path) -> Row:
        # TODO: might want to generalize the type conversion here into BaseCRUD
        return self.get_by_unique_col(conn, str(path))

    def get_many_by_path(self, conn: Connection, paths: Sequence[Path]) -> list[Row]:
        return self.get_many_by_unique_col(conn, [*map(str, paths)])

    def get_or_create(self, conn: Connection, path: Path) -> Row:
        q = """
                INSERT INTO file (path) VALUES (?)
                ON CONFLICT(path) DO UPDATE SET path=path --no-op update
                RETURNING id
            """
        return conn.execute(q, (str(path),)).fetchone()

    def get_or_create_many(self, conn: Connection, paths: list[Path]) -> list[Row]:
        vals = _placeholders(len(paths), "(?)")
        q = f"""
                INSERT INTO file (path) VALUES {vals}
                ON CONFLICT(path) DO UPDATE SET path=path --no-op update
                RETURNING id
            """

        return conn.execute(q, [*map(str, paths)]).fetchall()


file = FileCRUD()
