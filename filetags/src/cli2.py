import re
import sqlite3
from pathlib import Path
from typing import Optional

import click

from filetags.src import crud
from filetags.src.db.connect import get_vault
from filetags.src.db.init import init_db
from filetags.src.models.node import Node
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


@cli.group(help="Tag management")
@click.pass_obj
def tag(vault: sqlite3.Connection):
    pass


@tag.command(help="Create new tag", name="create")
@click.option("-n", "--name", type=click.STRING, required=True)
@click.option("-c", "--category", type=click.STRING)
@click.pass_obj
def new_tag(vault: sqlite3.Connection, name: str, category: Optional[str]):
    with vault as conn:
        crud.tag.create_tag(conn, name, category)


@tag.command(help="Edit tag", name="edit")
@click.argument("tag", nargs=-1, type=click.STRING, required=True)
@click.option("-n", "--name", type=click.STRING)
@click.option("-c", "--category", type=click.STRING)
@click.option(
    "--clear-category", type=click.BOOL, is_flag=True, help="Sets category to null."
)
@click.pass_obj
def edit_tag(vault: sqlite3.Connection, tag: list[str], clear_category: bool, **kwargs):
    if len(tag) > 1 and kwargs["name"]:
        raise click.BadArgumentUsage(
            "--name can't be present when multiple tags are given."
        )

    if not (any(kwargs.values()) or clear_category):
        raise click.BadArgumentUsage("Provide at least one option.")

    if clear_category and kwargs["category"]:
        raise click.BadArgumentUsage("Can't both set and clear category.")

    data = {k: v for k, v in kwargs.items() if v is not None}

    if clear_category:
        data["category"] = None

    with vault as conn:
        crud.tag.update_tags(
            conn,
            tag,
            data,
        )


@tag.command(help="Replace all instances of a tag.", name="replace")
@click.argument("old", nargs=-1, type=click.STRING, required=True)
@click.option("-n", "--new", type=click.STRING)
@click.option(
    "--remove",
    type=click.BOOL,
    is_flag=True,
    help="Remove the replaced tags entirely.",
)
@click.pass_obj
def replace_tag(
    vault: sqlite3.Connection, old: tuple[str, ...], new: str, remove: bool
):
    with vault as conn:
        new_id = crud.tag.get_tag_by_name(conn, new)[0]
        for tag in old:
            old_id = crud.tag.get_tag_by_name(conn, tag)[0]
            crud.file_tag.replace_file_tag(conn, old_id, new_id)

            if remove:
                crud.tag.delete_tag(conn, old_id)


@tag.command(help="Removes all instances of a tag.", name="delete")
@click.argument("tags", nargs=-1, type=click.STRING, required=True)
@click.pass_obj
def remove_tag(vault: sqlite3.Connection, tags: tuple[str, ...]):
    click.confirm(
        "Are you sure? This will also delete all child filetags of deleted tags.",
        abort=True,
    )

    with vault as conn:
        for tag in tags:
            tag_id = crud.tag.get_tag_by_name(conn, tag)[0]
            crud.tag.delete_tag(conn, tag_id)


def compile_pattern(pattern: str, ignore_case: bool):
    if not pattern:
        return None

    flags = re.IGNORECASE if ignore_case else 0

    return re.compile(pattern, flags)


@tag.command(help="List tags", name="ls")
@click.option("-l", "long", type=click.BOOL, is_flag=True, help="Long listing format.")
@click.option("-p", "--pattern", help="Filter output by regex pattern")
@click.option("-i", "--ignore-case", is_flag=True)
@click.option("-v", "--invert-match", is_flag=True)
@click.pass_obj
def list_tags(
    vault: sqlite3.Connection,
    long: bool,
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
):
    with vault as conn:
        tags = crud.tag.get_all_tags(conn)

    regex = compile_pattern(pattern, ignore_case)

    for i, name, category in tags:
        matched = bool(regex.search(name)) if regex else True

        if invert_match:
            matched = not matched

        if matched:
            click.echo(name + (f" ({category})" if long else ""))


def main():
    cli()


if __name__ == "__main__":
    main()
