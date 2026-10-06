from collections.abc import Callable
from pathlib import Path
from sqlite3 import Connection

import click

from tagumori.db.connect import get_connection
from tagumori.vault import Vault


class LazyVault:
    """Lazily gets vault only when it is truly accessed."""

    def __init__(self, get_path: Callable[[], Path | None], ctx: click.Context):
        self._get_path = get_path
        self._ctx = ctx
        self._conn: Connection | None = None

    @property
    def path(self) -> Path:
        p = self._get_path()
        if p is None or not p.exists():
            raise click.ClickException(
                "Vault not found. Run `tagumori db init` to create"
            )
        return self._get_path()

    def _get_conn(self) -> Connection:
        if self._conn is None:
            self._conn = self._ctx.with_resource(get_connection(self.path))

        return self._conn

    def __enter__(self) -> Vault:
        conn = self._get_conn()
        conn.__enter__()
        return Vault(conn)

    def __exit__(self, *args):
        # self._conn is basically guaranteed to exist, but this makes mypy happy
        assert self._conn is not None

        return self._conn.__exit__(*args)
