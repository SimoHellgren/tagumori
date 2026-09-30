import re
from pathlib import Path
from random import random

import click

from tagumori import service
from tagumori.commands.common import file_print_options, query_options, regex_options
from tagumori.commands.context import LazyVault
from tagumori.models import Query
from tagumori.query.ast import Expr
from tagumori.render import format_file_output


@click.group(help="Query management.")
@click.pass_obj
def query(vault: LazyVault):
    pass


@query.command(help="Save a query")
@click.argument("name", type=str)
@query_options
@regex_options
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrites existing query if present.",
)
@click.pass_obj
def save(
    lazy_vault: LazyVault,
    name: str,
    select: Expr | None,
    exclude: Expr | None,
    ignore_tag_case: bool,
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
    force: bool,
):
    with lazy_vault as vault:
        if not force and vault.queries.get_by_name(name):
            raise click.ClickException(
                f"Query '{name}' already exists. Run with --force to overwrite."
            )

        import json

        selects = [str(select)] if select else []
        excludes = [str(exclude)] if exclude else []

        vault.queries.upsert(
            name=name,
            select_tags=json.dumps(selects),
            exclude_tags=json.dumps(excludes),
            ignore_tag_case=ignore_tag_case,
            pattern=pattern,
            ignore_case=ignore_case,
            invert_match=invert_match,
        )


@query.command(help="Run saved queries")
@click.argument("pattern", type=str, default=r".*")
@file_print_options
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
    lazy_vault: LazyVault,
    pattern: str,
    long: bool,
    relative_to: Path,
    prefix: str,
    write: Path | None,
    shuffle: bool,
):

    with lazy_vault as vault:
        queries = vault.queries.get_all()

        for query in queries:
            if not re.match(pattern, query.name):
                continue

            files = service.list_files(
                vault,
                query.select_tags,
                query.exclude_tags,
                bool(query.ignore_tag_case),
                query.pattern,
                bool(query.ignore_case),
                bool(query.invert_match),
                long,
            )

            output_lines = format_file_output(files, relative_to, prefix)

            if shuffle:
                # mutation but oh well
                # also a bit of a silly hack to make mypy happy
                # (format_file_output is a generator, so this one has to be one, too).
                output_lines = (x for x in sorted(output_lines, key=lambda x: random()))

            if write:
                path = write / query.name

                click.echo(f"Writing {path}")
                with open(path, "w") as f:
                    for msg in output_lines:
                        click.echo(msg, f)

            else:
                click.echo(f"[{query.name}]")
                for msg in output_lines:
                    click.echo(msg)
                click.echo()


def ls_long_format(data: Query):

    selects = f"-s {x}" if (x := data.select_tags) else ""
    excludes = f"-e {x}" if (x := data.exclude_tags) else ""

    flag_map = [
        ("-I", data.ignore_tag_case),
        ("-i", data.ignore_case),
        ("-v", data.invert_match),
    ]
    flags = " ".join(f for f, v in flag_map if v)

    return f"{selects} {excludes} -p {data.pattern} {flags}".strip()


@query.command(help="List all saved queries.")
@click.option("-l", "--long", is_flag=True)
@click.pass_obj
def ls(lazy_vault: LazyVault, long: bool):
    with lazy_vault as vault:
        records = sorted(vault.queries.get_all(), key=lambda x: x.name)

    for record in records:
        msg = click.style(record.name, fg="yellow")

        if long:
            msg += click.style(f" {ls_long_format(record)}", fg="blue")

        click.echo(msg)


@query.command(help="Delete query.")
@click.argument("name", nargs=-1, type=str)
@click.pass_obj
def drop(lazy_vault: LazyVault, name: tuple[str, ...]):
    with lazy_vault as vault:
        for name_ in name:
            record = vault.queries.get_by_name(name_)
            if not record:
                raise click.ClickException(f"Query {name_} not found.")
            vault.queries.delete(record.id)
