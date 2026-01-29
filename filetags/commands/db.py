import sqlite3
from datetime import datetime
from pathlib import Path

import click

from filetags import service
from filetags.commands.context import LazyVault
from filetags.db.init import init_db
from filetags.models.node import Node


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

    with vault as source:
        with sqlite3.connect(backup_path) as destination:
            source.backup(destination)

    click.echo(f"Backup created: {backup_path}")


@db.command(help="Migrate legacy json vault into SQLite.")
@click.argument("json-vault", type=click.Path(path_type=Path, exists=True))
@click.pass_obj
def migrate_json(vault: LazyVault, json_vault: Path):
    import json

    from filetags import crud

    with open(json_vault) as f:
        data = json.load(f)

    def parse(tag: dict):
        name = tag["name"]
        children = [parse(c) for c in tag["children"]]
        return Node(name, children)

    with vault as conn:
        for entry in data["entries"]:
            path = Path(entry["name"])
            tags = [parse(c) for c in entry["children"]]

            service.add_tags_to_files(conn, [path], tags, False)

        sources, targets = zip(*data["tagalongs"])
        source_rows = crud.tag.get_or_create_many(conn, sources)
        target_rows = crud.tag.get_or_create_many(conn, targets)

        for source, target in zip(source_rows, target_rows):
            crud.tagalong.create(conn, source["id"], target["id"])

        crud.tagalong.apply(conn)


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
    """Simply reapplies schema.sql - assumes idempotent query.
    Will reassess if needed.
    """
    from filetags.db.init import SCHEMA_PATH

    with vault as conn:
        conn.executescript(SCHEMA_PATH.read_text())

    click.echo("Schema updated")
