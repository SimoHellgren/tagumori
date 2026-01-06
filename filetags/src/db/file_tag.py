from sqlite3 import Connection

from filetags.src.models.node import Node


def resolve_path(conn: Connection, file_id: int, path: tuple[Node]):
    parent_id = None
    for node in path:
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
            (file_id, node.value, parent_id, parent_id),
        ).fetchone()

        if not row:
            return None

        parent_id = row[0]

    return parent_id


def attach_tag(
    conn: Connection, file_id: int, tag_id: int, parent_id: int | None = None
):
    (file_tag_id,) = conn.execute(
        """
            INSERT INTO file_tag(file_id, tag_id, parent_id) VALUES (?,?,?)
            ON CONFLICT DO UPDATE SET file_id = file_id
            RETURNING id
        """,
        (file_id, tag_id, parent_id),
    ).fetchone()

    return file_tag_id


def detach_tag(conn: Connection, file_tag_id: int):
    conn.execute("DELETE FROM file_tag WHERE id = ?", (file_tag_id,))
