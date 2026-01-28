from pathlib import Path

import click

from filetags import crud, service
from filetags.commands.context import LazyVault
from filetags.utils import format_file_output


@click.group(help="Query management.")
@click.pass_obj
def query(vault: LazyVault):
    pass


@query.command(help="Save a query")
@click.argument("name", type=str)
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
    "-f",
    "--force",
    is_flag=True,
    help="Overwrites existing query if present.",
)
@click.pass_obj
def save(
    vault: LazyVault,
    name: str,
    select: tuple[str, ...],
    exclude: tuple[str, ...],
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
    force: bool,
):
    import json

    data = {
        "name": name,
        "select_tags": json.dumps(list(select)),
        "exclude_tags": json.dumps(list(exclude)),
        "pattern": pattern,
        "ignore_case": ignore_case,
        "invert_match": invert_match,
    }

    with vault as conn:
        if force:
            crud.query.upsert(conn, **data)

        else:
            # check if exists
            if crud.query.get_by_name(conn, name):
                raise click.ClickException(
                    f"Query '{name}' already exists. Run with --force to overwrite."
                )
            crud.query.create(conn, **data)


@query.command(help="Run a saved query")
@click.argument("name", type=str)
@click.option(
    "-l", "--long", type=click.BOOL, is_flag=True, help="Long listing format."
)
@click.option(
    "--relative-to",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path("."),
    help="Display paths relative to given directory.",
)
@click.option("--prefix", default="")
@click.pass_obj
def run(vault: LazyVault, name: str, long: bool, relative_to: Path, prefix: str):
    """POC implementation"""
    import json

    from filetags.parser import parse

    with vault as conn:
        params = crud.query.get_by_name(conn, name)

        select_nodes = [parse(n) for n in json.loads(params["select_tags"])]
        exclude_nodes = [parse(n) for n in json.loads(params["exclude_tags"])]

        paths = service.execute_query(
            conn,
            select_nodes,
            exclude_nodes,
            params["pattern"],
            bool(params["ignore_case"]),
            bool(params["invert_match"]),
        )

        if long:
            files_with_tags = service.get_files_with_tags(conn, paths)

        else:
            files_with_tags = {f: {} for f in paths}

    for msg in format_file_output(files_with_tags, long, relative_to, prefix):
        click.echo(msg)


@query.command(help="List all saved queries.")
@click.pass_obj
def ls(vault: LazyVault):
    with vault as conn:
        records = crud.query.get_all(conn)

    for record in records:
        click.echo(dict(record))


@query.command(help="Delete query.")
@click.argument("name", nargs=-1, type=str)
@click.pass_obj
def drop(vault: LazyVault, name: tuple[str, ...]):
    with vault as conn:
        for name_ in name:
            record = crud.query.get_by_name(conn, name_)
            crud.query.delete(conn, record["id"])
