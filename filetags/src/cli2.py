import sqlite3
from pathlib import Path

import click

from filetags.src import crud
from filetags.src.db.connect import get_vault
from filetags.src.db.init import init_db
from filetags.src.models.node import Node
from filetags.src.newcli import tag_cli
from filetags.src.parser import parse
from filetags.src.utils import flatten

VAULT_PATH = Path("vault.db")


@click.group()
@click.option(
    "--vault",
    type=click.Path(path_type=Path),
    default="./vault.db",
    help="Path to vault file, default ./vault.db",
)
@click.pass_context
def cli(ctx: click.Context, vault: Path):
    # skip checking / getting connection if running init
    if ctx.invoked_subcommand == "init":
        return

    if not vault.exists():
        raise click.ClickException(
            f"{vault} does not exist. Run `ftag init {vault}` to create"
        )

    ctx.obj = ctx.with_resource(get_vault(vault))


cli.add_command(tag_cli.tag)


@cli.command(help="Initialize empty vault")
@click.argument("filepath", type=click.Path(path_type=Path), default="vault.db")
def init(filepath: Path):
    if filepath.exists():
        click.echo(f"{filepath} already exists.")

    else:
        init_db(filepath)
        click.echo(f"{filepath} created.")


def attach_tree(conn, file_id, node, parent_id=None):
    tag_id = crud.tag.get_or_create_tag(conn, node.value)
    filetag_id = crud.file_tag.attach_tag(conn, file_id, tag_id, parent_id)
    for child in node.children:
        attach_tree(conn, file_id, child, filetag_id)


@cli.command(help="Add tags to files")
@click.option(
    "-f",
    "files",
    required=True,
    type=click.Path(path_type=Path, exists=True),
    multiple=True,
)
@click.option("-t", "tags", required=True, type=click.STRING, multiple=True)
@click.pass_obj
def add(vault: sqlite3.Connection, files: tuple[Path, ...], tags: tuple[str, ...]):
    root_tags = flatten(parse(t).children for t in tags)

    with vault as conn:
        for file in files:
            file_id = crud.file.get_or_create_file(conn, file)
            for root in root_tags:
                attach_tree(conn, file_id, root)


@cli.command(help="Remove tags from files")
@click.option(
    "-f",
    "files",
    required=True,
    type=click.Path(path_type=Path, exists=True),
    multiple=True,
)
@click.option("-t", "tags", required=True, type=click.STRING, multiple=True)
@click.pass_obj
def remove(vault: sqlite3.Connection, files: tuple[Path, ...], tags: tuple[str, ...]):
    root_tags = flatten(parse(t).children for t in tags)

    with vault as conn:
        for file in files:
            file_id = crud.file.get_or_create_file(conn, file)

            for root in root_tags:
                for path in root.paths_down():
                    file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
                    if file_tag_id:
                        crud.file_tag.detach_tag(conn, file_tag_id)


@cli.command(help="Show tags of files")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path))
@click.pass_obj
def show(vault: sqlite3.Connection, files: tuple[Path, ...]):
    with vault as conn:
        for file in files:
            file_id = crud.file.get_or_create_file(conn, file)
            tags = crud.file_tag.get_file_tags(conn, file_id)

            roots = crud.file_tag.build_tree(tags)

            click.echo(
                click.style(file, fg="green")
                + "\t"
                + click.style(",".join(str(root) for root in roots), fg="cyan")
            )


@cli.command(help="Replace tags on files", name="set")
@click.option(
    "-f",
    "files",
    required=True,
    type=click.Path(path_type=Path, exists=True),
    multiple=True,
)
@click.option("-t", "tags", required=True, type=click.STRING, multiple=True)
@click.pass_obj
def set_(vault: sqlite3.Connection, files: tuple[Path, ...], tags: tuple[str, ...]):
    root = Node("root", list(flatten(parse(t).children for t in tags)))
    _, *nodes = root.preorder()

    desired_paths = set(tuple(n.path()[1:]) for n in nodes)

    with vault as conn:
        for file in files:
            file_id = crud.file.get_or_create_file(conn, file)

            # attach new tags
            for node in root.children:
                attach_tree(conn, file_id, node)

            # remove other tags
            tags = crud.file_tag.get_file_tags(conn, file_id)

            roots = crud.file_tag.build_tree(tags)
            db_nodes = flatten(n.preorder() for n in roots)
            existing_paths = set(n.path() for n in db_nodes)

            paths_to_delete = existing_paths - desired_paths
            for path in paths_to_delete:
                file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
                crud.file_tag.detach_tag(conn, file_tag_id)


def main():
    cli()


if __name__ == "__main__":
    main()
