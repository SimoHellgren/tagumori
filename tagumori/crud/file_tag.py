from sqlite3 import Connection


class FileTagCrud:
    def __init__(self, conn: Connection):
        self._conn = conn

    def replace(self, old_id: int, new_id: int) -> None:
        self._conn.execute(
            "UPDATE file_tag SET tag_id = ? where tag_id = ?", (new_id, old_id)
        )

    def attach(self, file_id: int, tag_id: int, parent_id: int | None = None) -> int:
        (file_tag_id,) = self._conn.execute(
            """
                INSERT INTO file_tag(file_id, tag_id, parent_id) VALUES (?,?,?)
                ON CONFLICT DO UPDATE SET file_id = file_id
                RETURNING id
            """,
            (file_id, tag_id, parent_id),
        ).fetchone()

        return file_tag_id

    def detach(self, file_tag_id: int) -> None:
        self._conn.execute("DELETE FROM file_tag WHERE id = ?", (file_tag_id,))

    def drop_for_file(self, file_id: int) -> None:
        self._conn.execute("DELETE FROM file_tag WHERE file_id = ?", (file_id,))
