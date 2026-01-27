import click

from filetags import crud, service
from filetags.commands.context import LazyVault


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
@click.pass_obj
def save(
    vault: LazyVault,
    name: str,
    select: tuple[str, ...],
    exclude: tuple[str, ...],
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
):
    import json

    with vault as conn:
        crud.query.create(
            conn,
            name,
            json.dumps(list(select)),
            json.dumps(list(exclude)),
            pattern,
            ignore_case,
            invert_match,
        )


@query.command(help="Run a saved query")
@click.argument("name", type=str)
@click.pass_obj
def run(vault: LazyVault, name: str):
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

    for path in paths:
        click.echo(path)
