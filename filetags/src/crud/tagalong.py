from sqlite3 import Connection


def add(conn: Connection, source_id: int, target_id: int):
    conn.execute(
        "INSERT OR IGNORE INTO tagalong(tag_id, tagalong_id) VALUES (?,?)",
        (source_id, target_id),
    )


def get_all_names(conn: Connection):
    result = conn.execute("""
        SELECT t.name, ta.name
        FROM tagalong
        JOIN tag t on tagalong.tag_id = t.id
        JOIN tag ta on tagalong.tagalong_id = ta.id
        ORDER BY t.name, ta.name
        """).fetchall()

    return result
