from sqlite3 import Connection

from tagumori.crud.base import BaseCRUD
from tagumori.models import Query


class QueryCRUD(BaseCRUD[Query]):
    def __init__(self, conn: Connection):
        super().__init__(conn, table="query", unique_col="name", model=Query)

    def get_by_name(self, name: str):
        return self.get_by_unique_col(name)

    def create(
        self,
        name: str,
        select_tags: str,
        exclude_tags: str,
        ignore_tag_case: bool,
        pattern: str,
        ignore_case: bool,
        invert_match: bool,
    ) -> Query:
        return self._one_or_raise(
            self._conn.execute(
                """
            INSERT INTO query(
                name,
                select_tags,
                exclude_tags,
                ignore_tag_case,
                pattern,
                ignore_case,
                invert_match
            ) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *
            """,
                (
                    name,
                    select_tags,
                    exclude_tags,
                    ignore_tag_case,
                    pattern,
                    ignore_case,
                    invert_match,
                ),
            ).fetchone()
        )

    def upsert(
        self,
        name: str,
        select_tags: str,
        exclude_tags: str,
        ignore_tag_case: bool,
        pattern: str,
        ignore_case: bool,
        invert_match: bool,
    ) -> Query:
        return self._one_or_raise(
            self._conn.execute(
                """
            INSERT INTO query(
                name,
                select_tags,
                exclude_tags,
                ignore_tag_case,
                pattern,
                ignore_case,
                invert_match
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (name) DO UPDATE
              SET
                name=excluded.name,
                select_tags=excluded.select_tags,
                exclude_tags=excluded.exclude_tags,
                ignore_tag_case=excluded.ignore_tag_case,
                pattern=excluded.pattern,
                ignore_case=excluded.ignore_case,
                invert_match=excluded.invert_match
            RETURNING *
            """,
                (
                    name,
                    select_tags,
                    exclude_tags,
                    ignore_tag_case,
                    pattern,
                    ignore_case,
                    invert_match,
                ),
            ).fetchone()
        )
