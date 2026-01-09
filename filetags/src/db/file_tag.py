from pathlib import Path
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


# TODO: consider if this belongs elsewhere or if should be "packaged" differently.
# As it stands, this is rather coupled with get_files_tags
def build_tree(file_tags: list) -> Node:
    roots: list[Node] = []
    nodes: dict[str | None, Node] = {}

    # construct nodes
    for id_, tag, parent_id in file_tags:
        nodes[id_] = Node(value=tag)

    # add children & record root nodes
    for id_, _, parent_id in file_tags:
        node = nodes[id_]
        if parent_id is None:
            roots.append(node)
        else:
            nodes[parent_id].add_child(node)

    return roots


def get_file_tags(conn: Connection, file_id: int):
    q = f"""
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
    result = conn.execute(q, (file_id,)).fetchall()
    return result


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
