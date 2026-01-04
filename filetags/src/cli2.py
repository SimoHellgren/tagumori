import sqlite3
from collections import defaultdict
from pathlib import Path

import click
from db.init import init_db

VAULT_PATH = Path("vault.db")


@click.group()
def cli():
    pass


@cli.command()
@click.argument("filepath", type=click.Path(path_type=Path), default="vault.db")
def init(filepath: Path):
    if filepath.exists():
        click.echo(f"{filepath} already exists.")

    else:
        init_db(filepath)
        click.echo(f"{filepath} created.")


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


if __name__ == "__main__":
    cli()
