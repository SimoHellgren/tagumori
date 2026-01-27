from sqlite3 import Connection, Row

from filetags.crud.base import BaseCRUD


class QueryCRUD(BaseCRUD):
    def get_by_name(self, conn: Connection, name: str) -> Row:
        return self.get_by_unique_col(conn, name)

    def create(
        self,
        conn: Connection,
        name: str,
        select_tags: str,
        exclude_tags: str,
        pattern: str,
        ignore_case: bool,
        invert_match: bool,
    ) -> Row:
        return conn.execute(
            """
            INSERT INTO query(
                name,
                select_tags,
                exclude_tags,
                pattern,
                ignore_case,
                invert_match
            ) VALUES (?, ?, ?, ?, ?, ?) RETURNING *
            """,
            (name, select_tags, exclude_tags, pattern, ignore_case, invert_match),
        ).fetchone()


query = QueryCRUD("query", "name")
