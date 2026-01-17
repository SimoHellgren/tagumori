from sqlite3 import Connection, Row
from typing import Iterable


def create(conn: Connection, source_id: int, target_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO tagalong(tag_id, tagalong_id) VALUES (?,?)",
        (source_id, target_id),
    )


def delete(conn: Connection, source_id: int, target_id: int) -> None:
    conn.execute(
        "DELETE FROM tagalong WHERE tag_id = ? AND tagalong_id = ?",
        (source_id, target_id),
    )


def get_all_names(conn: Connection) -> list[Row]:
    result = conn.execute("""
        SELECT t.name, ta.name
        FROM tagalong
        JOIN tag t on tagalong.tag_id = t.id
        JOIN tag ta on tagalong.tagalong_id = ta.id
        ORDER BY t.name, ta.name
        """).fetchall()

    return result


def apply(conn: Connection, file_ids: Iterable[int] | None = None) -> None:
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

    conn.execute(q, tuple(file_ids or []))
