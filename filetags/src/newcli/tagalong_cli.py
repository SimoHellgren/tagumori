from sqlite3 import Connection

import click

from filetags.src import crud


@click.group(help="Tagalong management")
@click.pass_obj
def tagalong(vault: Connection):
    pass


@tagalong.command(help="Register new tagalongs.")
@click.option("-t", "--tag", required=True, multiple=True)
@click.option("-ta", "--tagalong", required=True, multiple=True)
@click.pass_obj
def add(vault: Connection, tag: tuple[str, ...], tagalong: tuple[str, ...]):
    with vault as conn:
        for source in tag:
            source_id = crud.tag.get_or_create_tag(conn, source)
            for target in tagalong:
                target_id = crud.tag.get_or_create_tag(conn, target)

                crud.tagalong.add(conn, source_id, target_id)

def remove():
    pass


@tagalong.command(help="Show all tagalongs.")
@click.pass_obj
def ls(vault: Connection):
    # TODO: Consider adding a grep-like filter if such would prove to be useful
    with vault as conn:
        for tag, tagalong in crud.tagalong.get_all_names(conn):
            click.echo(f"{tag} -> {tagalong}")


def apply():
    pass
