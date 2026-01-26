from pathlib import Path
from sqlite3 import Connection

import click

from filetags.db.connect import get_vault


class LazyVault:
    """Lazily gets vault only when it is truly accessed."""

    def __init__(self, path: Path, ctx: click.Context):
        self._path = path
        self._ctx = ctx
        self._conn: Connection | None = None

    def _get_conn(self) -> Connection:
        if self._conn is None:
            if not self._path.exists():
                raise click.ClickException(
                    f"{self._path} does not exist. Run `ftag db init {self._path}` to create"
                )

            self._conn = self._ctx.with_resource(get_vault(self._path))

        return self._conn

    def __enter__(self) -> Connection:
        return self._get_conn().__enter__()

    def __exit__(self, *args):
        return self._conn.__exit__(*args)
