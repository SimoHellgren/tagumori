from pathlib import Path

import click

from filetags import service
from filetags.commands import db, file, query, tag, tagalong
from filetags.commands.context import LazyVault
from filetags.models.node import Node
from filetags.parser import parse
from filetags.utils import flatten

DEFAULT_VAULT_PATH = Path("./vault.db")


@click.group()
@click.option(
    "--vault",
    type=click.Path(path_type=Path),
    default=DEFAULT_VAULT_PATH,
    help=f"Path to vault file, default {DEFAULT_VAULT_PATH}",
)
@click.pass_context
def cli(ctx: click.Context, vault: Path):
    ctx.obj = LazyVault(vault, ctx)


cli.add_command(tag.tag)
cli.add_command(tagalong.tagalong)
cli.add_command(db.db)
cli.add_command(file.file)
cli.add_command(query.query)


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
    vault: LazyVault,
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
def remove(vault: LazyVault, files: tuple[Path, ...], tags: tuple[str, ...]):
    root_tags = list(flatten(parse(t).children for t in tags))

    with vault as conn:
        service.remove_tags_from_files(conn, files, root_tags)


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
    vault: LazyVault, files: tuple[Path, ...], tags: tuple[str, ...], tagalongs: bool
):
    root = Node("root", list(flatten(parse(t).children for t in tags)))

    with vault as conn:
        service.set_tags_on_files(conn, files, root, tagalongs)


@cli.command(help="Drop files' tags")
@click.option(
    "-f",
    "files",
    required=True,
    type=click.Path(path_type=Path),
    multiple=True,
)
@click.option("--retain-file", type=click.BOOL, is_flag=True)
@click.pass_obj
def drop(vault: LazyVault, files: tuple[int, ...], retain_file: bool):
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
    vault: LazyVault,
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

    # TODO: some double-fetching here, still, but better than before
    # TODO: if not --long, could no need to fetch tags.
    with vault as conn:
        paths = service.execute_query(
            conn, select_nodes, exclude_nodes, pattern, ignore_case, invert_match
        )

        files_with_tags = service.get_files_with_tags(conn, paths)

    for path, data in files_with_tags.items():
        roots = data["roots"]
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


def main():
    cli()


if __name__ == "__main__":
    main()
