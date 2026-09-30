from sqlite3 import Connection

MIGRATIONS = {
    3: [
        "ALTER TABLE query ADD COLUMN ignore_tag_case BOOLEAN DEFAULT FALSE",
    ],
    4: [
        "CREATE INDEX IF NOT EXISTS idx_file_tag_parent_id ON file_tag(parent_id)",
    ],
}

LATEST_VERSION = max(MIGRATIONS.keys())


def migrate(conn: Connection):
    (current_version,) = conn.execute("PRAGMA user_version").fetchone()

    for version in range(current_version + 1, LATEST_VERSION + 1):
        for statement in MIGRATIONS[version]:
            conn.execute(statement)

    conn.execute(f"PRAGMA user_version = {LATEST_VERSION}")
