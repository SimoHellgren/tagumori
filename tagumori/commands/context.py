from pathlib import Path
from sqlite3 import Connection

import click

from tagumori.db.connect import get_vault
from tagumori.vault import Vault


class LazyVault:
    """Lazily gets vault only when it is truly accessed."""

    def __init__(self, path: Path, ctx: click.Context):
        self._path = path
        self._ctx = ctx
        self._conn: Connection | None = None

    @property
    def path(self) -> Path:
        return self._path

    def _get_conn(self) -> Connection:
        if self._conn is None:
            if not self._path.exists():
                raise click.ClickException(
                    f"{self._path} does not exist. Run `ftag db init {self._path}` to create"
                )

            self._conn = self._ctx.with_resource(get_vault(self._path))

        return self._conn

    def __enter__(self) -> Vault:
        conn = self._get_conn()
        conn.__enter__()
        return Vault(conn)

    def __exit__(self, *args):
        # self._conn is basically guaranteed to exist, but this makes mypy happy
        assert self._conn is not None

        return self._conn.__exit__(*args)
