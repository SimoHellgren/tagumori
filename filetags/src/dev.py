import json
import sqlite3
from itertools import chain
from pathlib import Path

VAULT_PATH = Path("vault.db")
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

flatten = chain.from_iterable


def mount(vault: Path, folder: Path):
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a directory")

    with sqlite3.connect(vault) as conn:
        for path in folder.glob("**/*"):
            if path.is_file():
                conn.execute(
                    "INSERT OR IGNORE INTO file (path) VALUES (?)", (str(path),)
                )


def transform(node):
    children = [transform(n) for n in node["children"]]

    return (node["name"], children)


def flatten_tree(node):
    yield node["name"]
    for child in node["children"]:
        yield from flatten_tree(child)


def load_json_vault(vault: Path, json_vault: str):
    with open(json_vault) as f:
        data = json.load(f)

    # create files, tags and adjacency list / edges
    for entry in data["entries"]:
        file_id = get_or_create_file(vault, Path(entry["name"]))

        _, tags = transform(entry)

        get_or_create_tags(vault, list(flatten_tree(entry))[1:])  # drop filename

        for tag in tags:
            add_filetags(vault, file_id, tag)

    # create tagalongs
    with sqlite3.connect(vault) as conn:
        tag_lookup = dict(conn.execute("SELECT name,id FROM tag").fetchall())

        for source, target in data["tagalongs"]:
            if source not in tag_lookup:
                source_row = get_or_create_tags(vault, [source])
                tag_lookup[source] = source_row[0][0]

            if target not in tag_lookup:
                target_row = get_or_create_tags(vault, [target])
                tag_lookup[target] = target_row[0][0]

            source_id = tag_lookup[source]
            target_id = tag_lookup[target]

            conn.execute(
                "INSERT INTO tagalong(tag_id, tagalong_id) VALUES (?,?)",
                (source_id, target_id),
            )


if __name__ == "__main__":
    load_json_vault(VAULT_PATH, "vault.json")
