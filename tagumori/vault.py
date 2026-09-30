from contextlib import contextmanager
from sqlite3 import Connection

from tagumori.crud.file import FileCRUD
from tagumori.crud.file_tag import FileTagCrud
from tagumori.crud.query import QueryCRUD
from tagumori.crud.tag import TagCRUD
from tagumori.crud.tagalong import TagalongCRUD


class Vault:
    def __init__(self, conn: Connection):
        self.conn = conn
        self.files = FileCRUD(conn)
        self.tags = TagCRUD(conn)
        self.queries = QueryCRUD(conn)
        self.file_tags = FileTagCrud(conn)
        self.tagalongs = TagalongCRUD(conn)

    @contextmanager
    def transaction(self):
        with self.conn:
            yield
