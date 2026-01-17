from sqlite3 import Connection
from typing import Optional

import click

from filetags import crud
from filetags.utils import compile_pattern


@click.group(help="Tag management")
@click.pass_obj
def tag(vault: Connection):
    pass


@tag.command(help="Create new tag", name="create")
@click.option("-n", "--name", type=click.STRING, required=True)
@click.option("-c", "--category", type=click.STRING)
@click.pass_obj
def new_tag(vault: Connection, name: str, category: Optional[str]):
    with vault as conn:
        crud.tag.create(conn, name, category)


@tag.command(help="Edit tag", name="edit")
@click.argument("tag", nargs=-1, type=click.STRING, required=True)
@click.option("-n", "--name", type=click.STRING)
@click.option("-c", "--category", type=click.STRING)
@click.option(
    "--clear-category", type=click.BOOL, is_flag=True, help="Sets category to null."
)
@click.pass_obj
def edit_tag(vault: Connection, tag: list[str], clear_category: bool, **kwargs):
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
        crud.tag.update(
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
def replace_tag(vault: Connection, old: tuple[str, ...], new: str, remove: bool):
    with vault as conn:
        new_record = crud.tag.get_or_create(conn, new)
        olds = crud.tag.get_many_by_name(conn, old)
        for old_record in olds:
            crud.file_tag.replace(conn, old_record["id"], new_record["id"])

            if remove:
                crud.tag.delete(conn, old_record["id"])


@tag.command(help="Removes all instances of a tag.", name="delete")
@click.argument("tags", nargs=-1, type=click.STRING, required=True)
@click.pass_obj
def remove_tag(vault: Connection, tags: tuple[str, ...]):
    click.confirm(
        "Are you sure? This will also delete all child filetags of deleted tags.",
        abort=True,
    )

    with vault as conn:
        for tag in tags:
            tag_id = crud.tag.get_by_name(conn, tag)[0]
            crud.tag.delete(conn, tag_id)


@tag.command(help="List tags", name="ls")
@click.option("-l", "long", type=click.BOOL, is_flag=True, help="Long listing format.")
@click.option("-p", "--pattern", help="Filter output by regex pattern", default=r".*")
@click.option("-i", "--ignore-case", is_flag=True)
@click.option("-v", "--invert-match", is_flag=True)
@click.pass_obj
def list_tags(
    vault: Connection,
    long: bool,
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
):
    with vault as conn:
        tags = crud.tag.get_all(conn)

    regex = compile_pattern(pattern, ignore_case)

    filtered = [t for t in tags if bool(regex.search(t["name"])) ^ invert_match]

    for tag in filtered:
        click.echo(tag["name"] + (f" ({tag['category']})" if long else ""))
