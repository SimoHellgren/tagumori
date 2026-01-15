from pathlib import Path
from sqlite3 import Connection, Row


def get_by_path(conn: Connection, path: Path) -> Row:
    return conn.execute("SELECT * FROM file WHERE path = ?", (path,)).fetchone()


def get_many_by_path(conn: Connection, paths: list[Path]) -> list[Row]:
    phs = ",".join("?" for _ in paths)
    return conn.execute(
        f"SELECT * FROM file WHERE path IN ({phs})", [*map(str, paths)]
    ).fetchall()


def get_many(conn: Connection, ids: list[int]) -> list[Row]:
    phs = ",".join("?" for _ in ids)
    return conn.execute(
        f"SELECT * FROM file WHERE id in ({phs}) ORDER BY path", ids
    ).fetchall()


def get_or_create(conn: Connection, file: Path) -> int:
    q = """
            INSERT INTO file (path) VALUES (?)
            ON CONFLICT(path) DO UPDATE SET path=path --no-op update
            RETURNING id
        """
    (file_id,) = conn.execute(q, (str(file),)).fetchone()

    return file_id


def get_or_create_many(conn: Connection, paths: list[Path]) -> list[Row]:
    vals = ",".join("(?)" for _ in paths)
    q = f"""
            INSERT INTO file (path) VALUES {vals}
            ON CONFLICT(path) DO UPDATE SET path=path --no-op update
            RETURNING id
        """

    return conn.execute(q, [*map(str, paths)]).fetchall()


def get_all(conn: Connection) -> list[Row]:
    return conn.execute("SELECT * FROM file ORDER BY path").fetchall()


def delete(conn: Connection, file_id: int):
    conn.execute("DELETE FROM file WHERE id = ?", (file_id,))
