from collections.abc import Sequence
from sqlite3 import Connection, Row

from filetags.crud.base import BaseCRUD, _placeholders


class TagCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(table="tag", unique_col="name")

    def get_by_name(self, conn: Connection, name: str) -> Row:
        return self.get_by_unique_col(conn, name)

    def get_many_by_name(self, conn: Connection, names: Sequence[str]) -> list[Row]:
        return self.get_many_by_unique_col(conn, names)

    def create(self, conn: Connection, name: str, category: str | None = None) -> Row:
        return conn.execute(
            "INSERT INTO tag(name, category) VALUES (?, ?) RETURNING *",
            (name, category),
        ).fetchone()

    def get_or_create(self, conn: Connection, name: str) -> Row:
        q = """
            INSERT INTO tag(name) VALUES (?)
            ON CONFLICT (name) DO UPDATE SET name=name --no-op
            RETURNING *
        """
        return conn.execute(q, (name,)).fetchone()

    def get_or_create_many(self, conn: Connection, names: list[str]) -> list[Row]:
        vals = _placeholders(len(names), "(?)")

        q = f"""
            INSERT INTO tag(name) VALUES {vals}
            ON CONFLICT (name) DO UPDATE SET name=name --no-op
            RETURNING id
        """

        return conn.execute(q, names).fetchall()

    def update(self, conn: Connection, names: list[str], data: dict) -> None:
        ALLOWED_COLS = {"name", "category"}

        if forbidden := (data.keys() - ALLOWED_COLS):
            raise ValueError(f"Forbidden column(s): {forbidden}")

        update_stmt = ",\n".join(f"{col} = ?" for col in data)
        name_phs = _placeholders(len(names))
        q = f"""
            UPDATE tag SET
                {update_stmt}
            WHERE name in ({name_phs})
        """

        vals = tuple([*data.values(), *names])
        conn.execute(q, vals)


tag = TagCRUD()
