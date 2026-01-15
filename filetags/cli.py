from pathlib import Path
from sqlite3 import Connection

import click

from filetags import crud, service
from filetags.commands import tag, tagalong
from filetags.db.connect import get_vault
from filetags.db.init import init_db
from filetags.models.node import Node
from filetags.parser import parse
from filetags.utils import compile_pattern, flatten

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


cli.add_command(tag.tag)
cli.add_command(tagalong.tagalong)


@cli.command(help="Initialize empty vault")
@click.argument("filepath", type=click.Path(path_type=Path), default="vault.db")
def init(filepath: Path):
    if filepath.exists():
        click.echo(f"{filepath} already exists.")

    else:
        init_db(filepath)
        click.echo(f"{filepath} created.")


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
    "--tagalongs/--no-tagalongs",
    type=click.BOOL,
    default=True,
    help="Apply / don't apply tagalongs.",
)
@click.pass_obj
def add(
    vault: Connection,
    files: tuple[Path, ...],
    tags: tuple[str, ...],
    tagalongs: bool,
):
    root_tags = list(flatten(parse(t).children for t in tags))

    with vault as conn:
        service.add_tags_to_files(conn, files, root_tags, tagalongs)


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
    root_tags = list(flatten(parse(t).children for t in tags))

    with vault as conn:
        service.remove_tags_from_files(conn, files, root_tags)


@cli.command(help="Show tags of files")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path))
@click.pass_obj
def show(vault: Connection, files: tuple[Path, ...]):
    with vault as conn:
        for file in files:
            file_id = crud.file.get_or_create(conn, file)
            tags = crud.file_tag.get_by_file_id(conn, file_id)

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
@click.option(
    "--tagalongs/--no-tagalongs",
    type=click.BOOL,
    default=True,
    help="Apply / don't apply tagalongs.",
)
@click.pass_obj
def set_(
    vault: Connection, files: tuple[Path, ...], tags: tuple[str, ...], tagalongs: bool
):
    root = Node("root", list(flatten(parse(t).children for t in tags)))

    with vault as conn:
        service.set_tags_on_files(conn, files, root, tagalongs)


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
            file_record = crud.file.get_by_path(conn, str(path))

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
@click.option("-p", "--pattern", help="Filter output by regex pattern")
@click.option("-i", "--ignore-case", is_flag=True)
@click.option(
    "-v",
    "--invert-match",
    is_flag=True,
    help="Inverts the regex match (not select/exclude).",
)
@click.pass_obj
def ls(
    vault: Connection,
    long: bool,
    select: tuple[str, ...],
    exclude: tuple[str, ...],
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
):
    # parse nodes
    select_nodes = [parse(n) for n in select]
    exclude_nodes = [parse(n) for n in exclude]

    include_ids = set()
    exclude_ids = set()

    regex = compile_pattern(pattern, ignore_case)

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

        ids = list(include_ids - exclude_ids)

        if ids:
            files = crud.file.get_many(conn, ids)
        else:
            files = crud.file.get_all(conn)

        for file_id, path, *_ in files:
            matched = bool(regex.search(path)) if regex else True

            if invert_match:
                matched = not matched

            if not matched:
                continue

            tags = crud.file_tag.get_by_file_id(conn, file_id)

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
