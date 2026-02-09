import re
from pathlib import Path
from random import random

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


@query.command(help="Run saved queries")
@click.argument("pattern", type=str, default=r".*")
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
@click.option(
    "-w",
    "--write",
    is_flag=False,
    type=click.Path(path_type=Path),
    flag_value=Path("."),
    help="Write results to files. Optionally specify output directory (default cwd).",
)
@click.option("--shuffle", is_flag=True, help="Randomize result order")
@click.pass_obj
def run(
    vault: LazyVault,
    pattern: str,
    long: bool,
    relative_to: Path,
    prefix: str,
    write: Path | None,
    shuffle: bool,
):
    import json

    with vault as conn:
        queries = crud.query.get_all(conn)

        for query in queries:
            if not re.match(pattern, query["name"]):
                continue

            select_strs = json.loads(query["select_tags"])
            exclude_strs = json.loads(query["exclude_tags"])

            paths = service.execute_query(
                conn,
                select_strs,
                exclude_strs,
                query["pattern"],
                bool(query["ignore_case"]),
                bool(query["invert_match"]),
            )

            if long:
                files_with_tags = service.get_files_with_tags(conn, paths)

            else:
                files_with_tags = {f: {} for f in paths}

            output_lines = format_file_output(
                files_with_tags, long, relative_to, prefix
            )

            if shuffle:
                # mutation but oh well
                output_lines = sorted(output_lines, key=lambda x: random())

            if write:
                path = write / query["name"]

                click.echo(f"Writing {path}")
                with open(path, "w") as f:
                    for msg in output_lines:
                        click.echo(msg, f)

            else:
                click.echo(f"[{query['name']}]")
                for msg in output_lines:
                    click.echo(msg)
                click.echo()


def ls_long_format(data: dict):
    import json

    selects = " ".join(f"-s {x}" for x in json.loads(data["select_tags"]))
    excludes = " ".join(f"-e {x}" for x in json.loads(data["exclude_tags"]))
    flags = (
        f"{'-i ' if data['ignore_case'] else ''}{'-v ' if data['invert_match'] else ''}"
    )

    return f"{selects} {excludes} -p {data['pattern']} {flags}".strip()


@query.command(help="List all saved queries.")
@click.option("-l", "--long", is_flag=True)
@click.pass_obj
def ls(vault: LazyVault, long: bool):
    with vault as conn:
        records = crud.query.get_all(conn)

    for record in records:
        msg = click.style(record["name"], fg="yellow")

        if long:
            msg += click.style(f" {ls_long_format(record)}", fg="blue")

        click.echo(msg)


@query.command(help="Delete query.")
@click.argument("name", nargs=-1, type=str)
@click.pass_obj
def drop(vault: LazyVault, name: tuple[str, ...]):
    with vault as conn:
        for name_ in name:
            record = crud.query.get_by_name(conn, name_)
            if not record:
                raise click.ClickException(f"Query {name_} not found.")
            crud.query.delete(conn, record["id"])
