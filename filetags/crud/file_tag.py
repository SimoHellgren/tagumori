from sqlite3 import Connection, Row


def resolve_path(conn: Connection, file_id: int, path: tuple[str, ...]) -> int:
    """Finds the lowest node of a path and returns file_tag.id if said path exists for file."""
    # TODO: this could probably be implemented as a special case of find_all, or at
    # least utilize similar recursive logic.
    parent_id = None
    for tag in path:
        row = conn.execute(
            """
            SELECT file_tag.id
            FROM file_tag
            JOIN tag on file_tag.tag_id = tag.id
            WHERE file_tag.file_id = ?
            AND tag.name = ?
            AND (
                file_tag.parent_id = ?
                OR (file_tag.parent_id IS NULL AND ? IS NULL)
            )
                    
        """,
            (file_id, tag, parent_id, parent_id),
        ).fetchone()

        if not row:
            return None

        parent_id = row["id"]

    return parent_id



def get_by_file_id(conn: Connection, file_id: int) -> list[Row]:
    q = """
        SELECT
            file_tag.id,
            tag.name,
            file_tag.parent_id
        FROM file_tag
        JOIN tag
            on tag.id = file_tag.tag_id
        WHERE file_tag.file_id = ?
        ORDER BY parent_id, name
    """
    return conn.execute(q, (file_id,)).fetchall()


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
