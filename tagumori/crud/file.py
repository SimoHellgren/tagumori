import sys
from collections.abc import Sequence
from pathlib import Path
from sqlite3 import Connection

from tagumori.crud.base import BaseCRUD, _placeholders
from tagumori.models import File
from tagumori.utils import flatten


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


class FileCRUD(BaseCRUD[File]):
    def __init__(self, conn: Connection):
        super().__init__(conn, table="file", unique_col="path", model=File)

    def get_by_path(self, path: Path) -> File | None:
        return self.get_by_unique_col(str(path.resolve()))

    def get_many_by_path(self, paths: Sequence[Path]) -> list[File]:
        return self.get_many_by_unique_col([str(p.resolve()) for p in paths])

    def get_by_inode(self, inode: int) -> list[File]:
        return self._many(
            self._conn.execute(
                "SELECT * FROM file WHERE inode = ?", (inode,)
            ).fetchall()
        )

    def get_or_create(self, path: Path) -> File:
        q = """
                INSERT INTO file (path, inode, device) VALUES (?,?,?)
                ON CONFLICT(path) DO UPDATE SET path=path --no-op update
                RETURNING *
            """

        inode, device = _get_inode_and_device(path)
        return self._one_or_raise(
            self._conn.execute(q, (str(path.resolve()), inode, device)).fetchone()
        )

    def get_or_create_many(self, paths: Sequence[Path]) -> list[File]:
        vals = _placeholders(len(paths), "(?,?,?)")
        q = f"""
                INSERT INTO file (path, inode, device) VALUES {vals}
                ON CONFLICT(path) DO UPDATE SET path=path --no-op update
                RETURNING *
            """
        params = [(str(p.resolve()), *_get_inode_and_device(p)) for p in paths]

        return self._many(self._conn.execute(q, tuple(flatten(params))).fetchall())

    def update(self, file_id: int, path: Path, inode: int, device: int) -> None:
        self._conn.execute(
            "UPDATE file SET path = ?, inode = ?, device = ? WHERE id = ?",
            (str(path.resolve()), inode, device, file_id),
        )
