import sqlite3
from datetime import datetime
from pathlib import Path

import click

from tagumori.commands.context import LazyVault
from tagumori.db.init import init_db


@click.group(help="Database management")
@click.pass_obj
def db(vault: LazyVault):
    pass


@db.command(help="Initialize empty vault")
@click.argument("filepath", type=click.Path(path_type=Path), default="vault.db")
def init(filepath: Path):
    if filepath.exists():
        click.echo(f"{filepath} already exists.")

    else:
        init_db(filepath)
        click.echo(f"{filepath} created.")


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
def backup(vault: LazyVault, dest: Path, directory: Path):
    if dest is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{vault._path.stem}-{timestamp}.db"

    else:
        backup_name = dest

    backup_path = directory / backup_name

    if backup_path.exists():
        click.confirm(f"{backup_path} already exists. Overwrite?", abort=True)
        backup_path.unlink()

    with vault as source, sqlite3.connect(backup_path) as destination:
        source.backup(destination)

    click.echo(f"Backup created: {backup_path}")


@db.command(help="Database info")
@click.pass_obj
def info(vault: LazyVault):
    with vault as conn:
        sqlite_version = conn.execute("SELECT sqlite_version()").fetchone()[0]
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        click.echo(f"SQLite version: {sqlite_version}")
        click.echo(f"Schema version: {user_version}")
        click.echo(f"Path: {vault._path}")
        click.echo(f"Size: {vault._path.stat().st_size / 1024:.1f} KB")
        click.echo(f"Modified: {datetime.fromtimestamp(vault._path.stat().st_mtime)}")
        click.echo()
        click.echo("Tables:")

        for (table_name,) in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            click.echo(f"  {table_name}: {count} rows")


@db.command(help="Migrate SQLite db to newest version")
@click.pass_obj
def migrate(vault: LazyVault):
    """Applies migrations on top of the schema.
    Will reassess if needed.
    """
    from tagumori.db.migrations import migrate

    with vault as conn:
        migrate(conn)

    click.echo("Schema updated")
