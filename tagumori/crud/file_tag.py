from sqlite3 import Connection


def replace(conn: Connection, old_id: int, new_id: int) -> None:
    conn.execute("UPDATE file_tag SET tag_id = ? where tag_id = ?", (new_id, old_id))


def attach(
    conn: Connection, file_id: int, tag_id: int, parent_id: int | None = None
) -> int:
    (file_tag_id,) = conn.execute(
        """
            INSERT INTO file_tag(file_id, tag_id, parent_id) VALUES (?,?,?)
            ON CONFLICT DO UPDATE SET file_id = file_id
            RETURNING id
        """,
        (file_id, tag_id, parent_id),
    ).fetchone()

    return file_tag_id


def detach(conn: Connection, file_tag_id: int) -> None:
    conn.execute("DELETE FROM file_tag WHERE id = ?", (file_tag_id,))


def drop_for_file(conn: Connection, file_id: int) -> None:
    conn.execute("DELETE FROM file_tag WHERE file_id = ?", (file_id,))
