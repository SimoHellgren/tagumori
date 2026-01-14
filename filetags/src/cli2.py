from pathlib import Path
from sqlite3 import Connection

import click

from filetags.src import crud
from filetags.src.db.connect import get_vault
from filetags.src.db.init import init_db
from filetags.src.models.node import Node
from filetags.src.newcli import tag_cli, tagalong_cli
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
cli.add_command(tagalong_cli.tagalong)


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
@click.option(
    "--no-tagalongs", type=click.BOOL, is_flag=True, help="Do not apply tagalongs."
)
@click.pass_obj
def add(
    vault: Connection,
    files: tuple[Path, ...],
    tags: tuple[str, ...],
    no_tagalongs: bool,
):
    root_tags = flatten(parse(t).children for t in tags)

    with vault as conn:
        for file in files:
            file_id = crud.file.get_or_create_file(conn, file)
            for root in root_tags:
                attach_tree(conn, file_id, root)

            if not no_tagalongs:
                crud.tagalong.apply(
                    conn,
                    [file_id],
                )


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
def remove(vault: Connection, files: tuple[Path, ...], tags: tuple[str, ...]):
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
def show(vault: Connection, files: tuple[Path, ...]):
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
def set_(vault: Connection, files: tuple[Path, ...], tags: tuple[str, ...]):
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


@cli.command(help="Drop files' tags")
@click.option(
    "-f",
    "files",
    required=True,
    type=click.Path(path_type=Path, exists=True),
    multiple=True,
)
@click.option("--retain-file", type=click.BOOL, is_flag=True)
@click.pass_obj
def drop(vault: Connection, files: tuple[int, ...], retain_file: bool):
    with vault as conn:
        for path in files:
            file_record = crud.file.get_by_name(conn, str(path))

            if not file_record:
                continue

            file_id = file_record[0]

            crud.file_tag.drop_for_file(conn, file_id)

            if not retain_file:
                crud.file.delete(conn, file_id)


@cli.command(help="List files (with optional filters).")
@click.option("-l", "long", type=click.BOOL, is_flag=True, help="Long listing format.")
@click.option("-s", "select", multiple=True)
@click.option("-e", "exclude", multiple=True)
@click.pass_obj
def ls(
    vault: Connection, long: bool, select: tuple[str, ...], exclude: tuple[str, ...]
):
    # parse nodes
    select_nodes = [parse(n) for n in select]
    exclude_nodes = [parse(n) for n in exclude]

    include_ids = set()
    exclude_ids = set()

    with vault as conn:
        for n in select_nodes:
            matches = []
            for _, *p in n.paths_down():
                matches.append({x[0] for x in crud.file_tag.find_all(conn, p)})

            include_ids |= set.intersection(*matches)

        for n in exclude_nodes:
            matches = []
            for _, *p in n.paths_down():
                matches.append({x[0] for x in crud.file_tag.find_all(conn, p)})

            exclude_ids |= set.intersection(*matches)

        files = crud.file.get_many(conn, list(include_ids - exclude_ids))

        for file_id, path, *_ in files:
            tags = crud.file_tag.get_file_tags(conn, file_id)

            roots = crud.file_tag.build_tree(tags)

            msg = click.style(path, fg="green")

            if long:
                msg += "\t" + click.style(
                    ",".join(str(root) for root in roots), fg="cyan"
                )

            click.echo(msg)


def main():
    cli()


if __name__ == "__main__":
    main()
