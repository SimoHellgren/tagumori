from sqlite3 import Connection


def get_or_create_tag(conn: Connection, tag: str) -> int:
    q = """
        INSERT INTO tag(name) VALUES (?)
        ON CONFLICT (name) DO UPDATE SET name=name --no-op
        RETURNING id
    """
    (tag_id,) = conn.execute(q, (tag,)).fetchone()

    return tag_id
