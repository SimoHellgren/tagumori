from sqlite3 import Connection, Row

from filetags.models.node import Node
from filetags.utils import flatten


def resolve_path(conn: Connection, file_id: int, path: tuple[Node, ...]) -> int:
    """Finds the lowest node of a path and returns file_tag.id if said path exists for file."""
    # TODO: this could probably be implemented as a special case of find_all, or at
    # least utilize similar recursive logic.
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


def find_all(conn: Connection, path: tuple[Node, ...]) -> list[Row]:
    values = ",".join("(?,?)" for _ in path)

    q = f"""
        WITH path(depth, tag_name) AS (
            VALUES {values}
        ),

        match(file_id, id, depth) AS (
            SELECT
                file_tag.file_id,
                file_tag.id,
                1
            FROM file_tag
            JOIN tag ON tag.id = file_tag.tag_id
            JOIN path
                ON path.depth = 1
                AND path.tag_name = tag.name

            UNION ALL

            SELECT
                child.file_id,
                child.id,
                parent.depth + 1
            FROM match parent
            JOIN file_tag child
                ON child.parent_id = parent.id
                AND child.file_id = parent.file_id
            JOIN tag ON child.tag_id = tag.id
            JOIN path
                ON path.depth = parent.depth + 1
                AND path.tag_name = tag.name 
        )

        SELECT DISTINCT file_id FROM match 
        WHERE depth = (SELECT MAX(depth) FROM path)
    """
    tags = (n.value for n in path)
    return conn.execute(q, tuple(flatten(enumerate(tags, 1)))).fetchall()


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


def replace(conn: Connection, old_id: int, new_id: int):
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


def drop_for_file(conn: Connection, file_id: int):
    conn.execute("DELETE FROM file_tag WHERE file_id = ?", (file_id,))
