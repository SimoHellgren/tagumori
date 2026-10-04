from collections.abc import Callable
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from sqlite3 import Connection

from tagumori.crud.file import FileCRUD
from tagumori.crud.file_tag import FileTagCrud
from tagumori.crud.query import QueryCRUD
from tagumori.crud.tag import TagCRUD
from tagumori.crud.tagalong import TagalongCRUD

CACHES = []


def datacache(func: Callable):
    wrapped = cache(func)

    CACHES.append(wrapped)

    return wrapped


class Vault:
    def __init__(self, path: Path, conn: Connection):
        self.path = path
        self.conn = conn
        self.files = FileCRUD(conn)
        self.tags = TagCRUD(conn)
        self.queries = QueryCRUD(conn)
        self.file_tags = FileTagCrud(conn)
        self.tagalongs = TagalongCRUD(conn)

        self.cache_version: int | None = None
        self.mtime: float | None = None

    @contextmanager
    def transaction(self):
        with self.conn:
            yield

    def _mtime(self):
        """Returns the 'true' mtime for the vault, considering both
        the db file itself as well as the write ahead log
        """
        db_mtime = self.path.stat().st_mtime

        try:
            wal_file = self.path.with_name(self.path.name + "-wal")
            wal_mtime = wal_file.stat().st_mtime
        except FileNotFoundError:
            return db_mtime

        return max(db_mtime, wal_mtime)

    def check_cache(self):
        """Clears cache if needed:
            1. stat db and wal files to determine whether the files have changed at all
            2. check sqlite's data_version to see if data is changed

        It is technically possible that this misses changes when two commits land
          at the same mtime tick and the cache check is run between those commits.
          However, near-simultaneous writes are deemed so unlikely that this risk
          won't be mitigated, at least for now.
        """
        mtime = self._mtime()

        # if db hasn't been edited, skip checking data version
        if self.mtime is not None and not mtime > self.mtime:
            return

        self.mtime = mtime

        (version,) = self.conn.execute("PRAGMA data_version").fetchone()

        if self.cache_version != version:
            self.cache_version = version

            for c in CACHES:
                c.cache_clear()
