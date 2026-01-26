import sys
from pathlib import Path
from sqlite3 import Connection, Row
from typing import Sequence

from filetags.crud.base import BaseCRUD, _placeholders
from filetags.utils import flatten


def _get_inode_and_device(path: Path) -> tuple[int | None, int | None]:
    """Get's inode and device if file exists, otherwise None.

    Skips is on Windows, because inode,device aren't really robust
    (and they are intended for finding files whose names have changed).

    Useful also for convenience in test where we don't actually
    create the files.
    """

    if sys.platform == "win32":
        return None, None

    try:
        stat = path.stat()
        return stat.st_ino, stat.st_dev

    except FileNotFoundError:
        return None, None


class FileCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(table="file", unique_col="path")

    def get_by_path(self, conn: Connection, path: Path) -> Row:
        # TODO: might want to generalize the type conversion here into BaseCRUD
        return self.get_by_unique_col(conn, str(path.resolve()))

    def get_many_by_path(self, conn: Connection, paths: Sequence[Path]) -> list[Row]:
        return self.get_many_by_unique_col(conn, [str(p.resolve()) for p in paths])

    def get_by_inode(self, conn: Connection, inode: int) -> list[Row]:
        return conn.execute("SELECT * FROM file WHERE inode = ?", (inode,)).fetchall()

    def get_or_create(self, conn: Connection, path: Path) -> Row:
        q = """
                INSERT INTO file (path, inode, device) VALUES (?,?,?)
                ON CONFLICT(path) DO UPDATE SET path=path --no-op update
                RETURNING *
            """

        inode, device = _get_inode_and_device(path)
        return conn.execute(q, (str(path.resolve()), inode, device)).fetchone()

    def get_or_create_many(self, conn: Connection, paths: list[Path]) -> list[Row]:
        vals = _placeholders(len(paths), "(?,?,?)")
        q = f"""
                INSERT INTO file (path, inode, device) VALUES {vals}
                ON CONFLICT(path) DO UPDATE SET path=path --no-op update
                RETURNING id
            """
        params = [(str(p.resolve()), *_get_inode_and_device(p)) for p in paths]

        return conn.execute(q, tuple(flatten(params))).fetchall()

    def update(
        self, conn: Connection, file_id: int, path: Path, inode: int, device: int
    ):
        conn.execute(
            "UPDATE file SET path = ?, inode = ?, device = ? WHERE id = ?",
            (str(path.resolve()), inode, device, file_id),
        )


file = FileCRUD()
