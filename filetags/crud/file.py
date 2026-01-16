from pathlib import Path
from sqlite3 import Connection, Row
from typing import Sequence

from filetags.crud.base import BaseCRUD


class FileCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(table="file", unique_col="path")

    def get_by_path(self, conn: Connection, path: Path) -> Row:
        # TODO: might want to generalize the type conversion here into BaseCRUD
        return self.get_by_unique_col(conn, str(path))

    def get_many_by_path(self, conn: Connection, paths: Sequence[Path]) -> list[Row]:
        return self.get_many_by_unique_col(conn, [*map(str, paths)])


file = FileCRUD()


def get_or_create(conn: Connection, file: Path) -> int:
    q = """
            INSERT INTO file (path) VALUES (?)
            ON CONFLICT(path) DO UPDATE SET path=path --no-op update
            RETURNING id
        """
    (file_id,) = conn.execute(q, (str(file),)).fetchone()

    return file_id


def get_or_create_many(conn: Connection, paths: list[Path]) -> list[Row]:
    vals = ",".join("(?)" for _ in paths)
    q = f"""
            INSERT INTO file (path) VALUES {vals}
            ON CONFLICT(path) DO UPDATE SET path=path --no-op update
            RETURNING id
        """

    return conn.execute(q, [*map(str, paths)]).fetchall()
