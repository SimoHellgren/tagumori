import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import click

from tagumori.commands.context import LazyVault
from tagumori.db.init import init_db
from tagumori.discovery import data_dir, pointer_path, read_pointer, vault_db_path


@click.group(help="Database management")
@click.pass_obj
def db(vault: LazyVault):
    pass


def _ensure_uninitialized(pointer: Path) -> None:
    # check pointer exists and is valid
    existing = read_pointer(pointer)
    if not existing:
        return

    if vault_db_path(existing).exists():
        raise click.ClickException(f"Already initialized (vault {existing}).")

    raise click.ClickException(f"{pointer} names vault {existing}, but db not found.")


def _new_db_dir() -> Path:
    import secrets

    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    while True:
        candidate = root / f"tagumori-{secrets.token_hex(3)}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate


@db.command(help="Initialize empty vault")
@click.argument(
    "directory", type=click.Path(path_type=Path, file_okay=False), default="."
)
def init(directory: Path):
    # check if already exists
    pointer = pointer_path(directory)
    _ensure_uninitialized(pointer)

    pointer.parent.mkdir(parents=True, exist_ok=True)
    db_dir = _new_db_dir()

    try:
        init_db(db_dir / "vault.db")
        pointer.write_text(db_dir.name)
    except BaseException:  # in case literally anything crashes the process
        shutil.rmtree(db_dir, ignore_errors=True)
        raise


@db.command(help="Create a backup of vault.")
@click.argument("dest", type=click.Path(path_type=Path), required=False)
@click.option(
    "-d",
    "--dir",
    "directory",
    type=click.Path(
        path_type=Path,
        file_okay=False,
    ),
    default=Path("."),
    help="Directory to save backup into.",
)
@click.pass_obj
def backup(lazy_vault: LazyVault, dest: Path, directory: Path):
    if dest is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{lazy_vault.path.stem}-{timestamp}.db"

    else:
        backup_name = dest

    backup_path = directory / backup_name

    if backup_path.exists():
        click.confirm(f"{backup_path} already exists. Overwrite?", abort=True)
        backup_path.unlink()

    with lazy_vault as source, sqlite3.connect(backup_path) as destination:
        source.conn.backup(destination)

    click.echo(f"Backup created: {backup_path}")


@db.command(help="Database info")
@click.pass_obj
def info(lazy_vault: LazyVault):
    with lazy_vault as vault:
        sqlite_version = vault.conn.execute("SELECT sqlite_version()").fetchone()[0]
        user_version = vault.conn.execute("PRAGMA user_version").fetchone()[0]
        tables = vault.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        click.echo(f"SQLite version: {sqlite_version}")
        click.echo(f"Schema version: {user_version}")
        click.echo(f"Path: {lazy_vault.path}")
        click.echo(f"Size: {lazy_vault.path.stat().st_size / 1024:.1f} KB")
        click.echo(
            f"Modified: {datetime.fromtimestamp(lazy_vault.path.stat().st_mtime)}"
        )
        click.echo()
        click.echo("Tables:")

        for (table_name,) in tables:
            count = vault.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[
                0
            ]
            click.echo(f"  {table_name}: {count} rows")


@db.command(help="Migrate SQLite db to newest version")
@click.pass_obj
def migrate(lazy_vault: LazyVault):
    """Applies migrations on top of the schema.
    Will reassess if needed.
    """
    from tagumori.db.migrations import migrate

    with lazy_vault as vault:
        migrate(vault.conn)

    click.echo("Schema updated")
