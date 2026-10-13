import sqlite3
from contextlib import closing
from pathlib import Path


def snapshot(source: sqlite3.Connection, dest: Path) -> None:
    with closing(sqlite3.connect(dest)) as destination:
        source.backup(destination)
