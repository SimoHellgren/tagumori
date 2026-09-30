from collections.abc import Sequence
from sqlite3 import Connection

from tagumori.crud.base import BaseCRUD, _placeholders
from tagumori.models import Tag


class TagCRUD(BaseCRUD[Tag]):
    def __init__(self, conn: Connection):
        super().__init__(conn, table="tag", unique_col="name", model=Tag)

    def get_by_name(self, name: str) -> Tag | None:
        return self.get_by_unique_col(name)

    def get_many_by_name(self, names: Sequence[str]) -> list[Tag]:
        return self.get_many_by_unique_col(names)

    def create(self, name: str, category: str | None = None) -> Tag:
        return self._one_or_raise(
            self._conn.execute(
                "INSERT INTO tag(name, category) VALUES (?, ?) RETURNING *",
                (name, category),
            ).fetchone()
        )

    def get_or_create(self, name: str) -> Tag:
        q = """
            INSERT INTO tag(name) VALUES (?)
            ON CONFLICT (name) DO UPDATE SET name=name --no-op
            RETURNING *
        """
        return self._one_or_raise(self._conn.execute(q, (name,)).fetchone())

    def get_or_create_many(self, names: Sequence[str]) -> list[Tag]:
        vals = _placeholders(len(names), "(?)")

        q = f"""
            INSERT INTO tag(name) VALUES {vals}
            ON CONFLICT (name) DO UPDATE SET name=name --no-op
            RETURNING *
        """

        return self._many(self._conn.execute(q, names).fetchall())

    def update(self, names: list[str], data: dict) -> None:
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

        vals = (*data.values(), *names)
        self._conn.execute(q, vals)
