import sqlite3
from datetime import datetime
from pathlib import Path

import click

from filetags.commands.context import LazyVault
from filetags.db.init import init_db


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
