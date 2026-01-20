from pathlib import Path
from sqlite3 import Connection

import click

from filetags import service
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
        files_with_tags = service.get_files_with_tags(conn, files)

    for path, roots in files_with_tags.items():
        click.echo(
            click.style(path, fg="green")
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
        service.drop_file_tags(conn, files, retain_file)


@cli.command(help="List files (with optional filters).")
@click.option(
    "-l", "--long", type=click.BOOL, is_flag=True, help="Long listing format."
)
@click.option("-s", "--select", multiple=True)
@click.option("-e", "--exclude", multiple=True)
@click.option("-p", "--pattern", help="Filter output by regex pattern.", default=r".*")
@click.option("-i", "--ignore-case", is_flag=True, help="Ignore regex case.")
@click.option(
    "-v",
    "--invert-match",
    is_flag=True,
    help="Inverts the regex match (not select/exclude).",
)
@click.option(
    "--relative-to",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path("."),
    help="Display paths relative to given directory.",
)
@click.option("--prefix", default="")
@click.pass_obj
def ls(
    vault: Connection,
    long: bool,
    select: tuple[str, ...],
    exclude: tuple[str, ...],
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
    relative_to: Path,
    prefix: str,
):
    # parse nodes
    select_nodes = [parse(n) for n in select]
    exclude_nodes = [parse(n) for n in exclude]

    regex = compile_pattern(pattern, ignore_case)

    # TODO: some double-fetching here, still, but better than before
    # TODO: if not --long, could no need to fetch tags.
    with vault as conn:
        files = service.search_files(conn, select_nodes, exclude_nodes)

        filtered = [f for f in files if bool(regex.search(f["path"])) ^ invert_match]

        files_with_tags = service.get_files_with_tags(
            conn, [Path(f["path"]) for f in filtered]
        )

    for path, roots in files_with_tags.items():
        try:
            # relative path
            display_path = prefix / path.relative_to(relative_to.resolve())

        except ValueError:
            # default to absolute path if not relative
            display_path = prefix / path

        msg = click.style(display_path, fg="green")

        if long:
            msg += "\t" + click.style(",".join(str(root) for root in roots), fg="cyan")

        click.echo(msg)


@cli.command(help="Migrate legacy json vault into SQLite.")
@click.argument("json-vault", type=click.Path(path_type=Path, exists=True))
@click.pass_obj
def migrate_json(vault: Connection, json_vault: Path):
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


def main():
    cli()


if __name__ == "__main__":
    main()
