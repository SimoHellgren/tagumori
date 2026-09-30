from collections.abc import Iterable
from sqlite3 import Connection


class TagalongCRUD:
    def __init__(self, conn: Connection):
        self._conn = conn

    def create(self, source_id: int, target_id: int) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO tagalong(tag_id, tagalong_id) VALUES (?,?)",
            (source_id, target_id),
        )

    def delete(self, source_id: int, target_id: int) -> None:
        self._conn.execute(
            "DELETE FROM tagalong WHERE tag_id = ? AND tagalong_id = ?",
            (source_id, target_id),
        )

    def apply(self, file_ids: Iterable[int] | None = None) -> None:
        # TODO: consider allowing tag filtering
        q = """
            WITH RECURSIVE implied(tag_id, tagalong_id) AS (
                -- direct tagalongs
                SELECT tag_id, tagalong_id
                FROM tagalong
                
                UNION
                
                -- indirect tagalongs
                SELECT implied.tag_id, t.tagalong_id
                FROM tagalong t
                JOIN implied ON t.tag_id = implied.tagalong_id
            )

            INSERT OR IGNORE INTO file_tag (file_id, tag_id, parent_id)
            SELECT
                file_tag.file_id,
                implied.tagalong_id tag_id,
                file_tag.parent_id
            FROM file_tag
            JOIN implied on implied.tag_id = file_tag.tag_id"""

        if file_ids:
            phs = ",".join("?" for _ in file_ids)
            q += f"\nWHERE file_tag.file_id IN ({phs})"

        self._conn.execute(q, tuple(file_ids or []))
