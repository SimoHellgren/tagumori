import sqlite3
from collections import defaultdict
from pathlib import Path

import click

from filetags.src.db.connect import get_vault
from filetags.src.db.file import get_or_create_file
from filetags.src.db.file_tag import attach_tag, detach_tag, resolve_path
from filetags.src.db.init import init_db
from filetags.src.db.tag import get_or_create_tag
from filetags.src.parser import parse
from filetags.src.utils import flatten

VAULT_PATH = Path("vault.db")


@click.group()
def cli():
    pass


@cli.command(help="Initialize empty vault")
@click.argument("filepath", type=click.Path(path_type=Path), default="vault.db")
def init(filepath: Path):
    if filepath.exists():
        click.echo(f"{filepath} already exists.")

    else:
        init_db(filepath)
        click.echo(f"{filepath} created.")


def attach_tree(conn, file_id, node, parent_id=None):
    tag_id = get_or_create_tag(conn, node.value)
    filetag_id = attach_tag(conn, file_id, tag_id, parent_id)
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
def add(files, tags):
    root_tags = flatten(parse(t).children for t in tags)

    with get_vault() as conn:
        for file in files:
            file_id = get_or_create_file(conn, file)
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
def remove(files, tags):
    root_tags = flatten(parse(t).children for t in tags)

    with get_vault() as conn:
        for file in files:
            file_id = get_or_create_file(conn, file)

            for root in root_tags:
                for path in root.paths_down():
                    file_tag_id = resolve_path(conn, file_id, path)
                    if file_tag_id:
                        detach_tag(conn, file_tag_id)


# testing stuff from this point down, to be refactored.
@cli.command()
@click.argument("filename", nargs=-1)
def show(filename):
    with sqlite3.connect(VAULT_PATH) as conn:
        placeholders = ",".join("?" for _ in filename)
        q = f"""
            SELECT
                file_tag.id,
                tag.name,
                file_tag.parent_id
            FROM file_tag
            JOIN file
                ON file.id = file_tag.file_id
            JOIN tag
                on tag.id = file_tag.tag_id
            WHERE file.path in ({placeholders})
            ORDER BY parent_id, name
        """
        result = conn.execute(q, filename).fetchall()

    children = defaultdict(list)
    names = {}

    for id_, tag, parent_id in result:
        names[id_] = tag
        children[parent_id].append(id_)

    def format_tags(id_):
        if id_ not in children:
            return names[id_]

        inner = ",".join(format_tags(child) for child in children[id_])

        return f"{names[id_]}[{inner}]"

    roots = children[None]
    for root in roots:
        print(format_tags(root))


def main():
    cli()


if __name__ == "__main__":
    main()
