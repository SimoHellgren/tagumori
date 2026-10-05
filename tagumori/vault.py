from collections.abc import Callable
from contextlib import contextmanager
from functools import cache
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
    def __init__(self, conn: Connection):
        self.conn = conn
        self.files = FileCRUD(conn)
        self.tags = TagCRUD(conn)
        self.queries = QueryCRUD(conn)
        self.file_tags = FileTagCrud(conn)
        self.tagalongs = TagalongCRUD(conn)

        self.cache_version: int | None = None

    @contextmanager
    def transaction(self):
        with self.conn:
            yield

    def check_cache(self):
        (version,) = self.conn.execute("PRAGMA data_version").fetchone()

        if self.cache_version != version:
            self.cache_version = version

            for c in CACHES:
                c.cache_clear()
