from itertools import product
from pathlib import Path

import click

from filetags import crud
from filetags.commands.context import LazyVault


@click.group(help="Tagalong management")
@click.pass_obj
def tagalong(vault: LazyVault):
    pass


@tagalong.command(help="Register new tagalongs.")
@click.option("-t", "--tag", required=True, multiple=True)
@click.option("-ta", "--tagalong", required=True, multiple=True)
@click.pass_obj
def add(vault: LazyVault, tag: tuple[str, ...], tagalong: tuple[str, ...]):
    with vault as conn:
        sources = crud.tag.get_or_create_many(conn, tag)
        targets = crud.tag.get_or_create_many(conn, tagalong)

        for source, target in product(sources, targets):
            crud.tagalong.create(conn, source["id"], target["id"])


@tagalong.command(help="Remove tagalongs.")
@click.option("-t", "--tag", required=True, multiple=True)
@click.option("-ta", "--tagalong", required=True, multiple=True)
@click.pass_obj
def remove(vault: LazyVault, tag: tuple[str, ...], tagalong: tuple[str, ...]):
    with vault as conn:
        sources = crud.tag.get_many_by_name(conn, tag)
        targets = crud.tag.get_many_by_name(conn, tagalong)

        for source, target in product(sources, targets):
            crud.tagalong.delete(conn, source["id"], target["id"])


@tagalong.command(help="Show all tagalongs.")
@click.pass_obj
def ls(vault: LazyVault):
    # TODO: Consider adding a grep-like filter if such would prove to be useful
    with vault as conn:
        for tag, tagalong in crud.tagalong.get_all_names(conn):
            click.echo(f"{tag} -> {tagalong}")


@tagalong.command(help="Apply all tagalongs (to all files by default).")
@click.option(
    "-f", "--file", type=click.Path(path_type=Path, exists=True), multiple=True
)
@click.pass_obj
def apply(vault: LazyVault, file: tuple[Path, ...]):
    # TODO: consider filtering by tag
    with vault as conn:
        files = crud.file.get_many_by_path(conn, file)
        file_ids = [f["id"] for f in files]

        crud.tagalong.apply(conn, file_ids)
