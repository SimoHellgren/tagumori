from pathlib import Path
from sqlite3 import Connection

from filetags import crud
from filetags.models.node import Node
from filetags.utils import flatten


def attach_tree(
    conn: Connection, file_id: int, node: Node, parent_id: int | None = None
):
    tag_id = crud.tag.get_or_create(conn, node.value)
    filetag_id = crud.file_tag.attach(conn, file_id, tag_id, parent_id)
    for child in node.children:
        attach_tree(conn, file_id, child, filetag_id)


def add_tags_to_files(
    conn: Connection, files: list[Path], tags: list[Node], apply_tagalongs: bool = True
):
    file_ids = [x["id"] for x in crud.file.get_or_create_many(conn, files)]

    for file_id in file_ids:
        for tag in tags:
            attach_tree(conn, file_id, tag)

    if apply_tagalongs:
        crud.tagalong.apply(
            conn,
            file_ids,
        )


def remove_tags_from_files(conn: Connection, files: list[Path], tags: list[Node]):
    # non-existing files are skipped here due to how get_many_by_path works.
    file_ids = [x["id"] for x in crud.file.get_many_by_path(conn, files)]

    for file_id in file_ids:
        for tag in tags:
            for path in tag.paths_down():
                file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
                if file_tag_id:
                    crud.file_tag.detach(conn, file_tag_id)


def set_tags_on_files(
    conn: Connection, files: list[Path], tag: Node, apply_tagalongs: bool = True
):
    # remove unwanted paths
    _, *nodes = tag.preorder()
    desired_paths = set(tuple(n.path()[1:]) for n in nodes)

    file_ids = [x["id"] for x in crud.file.get_or_create_many(conn, files)]

    for file_id in file_ids:
        tags = crud.file_tag.get_by_file_id(conn, file_id)

        roots = crud.file_tag.build_tree(tags)
        db_nodes = flatten(n.preorder() for n in roots)
        existing_paths = set(n.path() for n in db_nodes)

        paths_to_delete = existing_paths - desired_paths
        for path in paths_to_delete:
            file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
            crud.file_tag.detach(conn, file_tag_id)

    # attach new tags - done after removal so new tagalongs aren't nuked.
    add_tags_to_files(conn, files, tag.children, apply_tagalongs)


def search_files(conn: Connection, select_tags: list[Node], exclude_tags: list[Node]):
    include_ids = set()
    exclude_ids = set()

    # TODO: refactor
    for n in select_tags:
        matches = []
        for _, *p in n.paths_down():
            matches.append({x[0] for x in crud.file_tag.find_all(conn, p)})

        include_ids |= set.intersection(*matches)

    for n in exclude_tags:
        matches = []
        for _, *p in n.paths_down():
            matches.append({x[0] for x in crud.file_tag.find_all(conn, p)})

        exclude_ids |= set.intersection(*matches)

    ids = tuple(include_ids - exclude_ids)

    if ids:
        files = crud.file.get_many(conn, ids)
    else:
        files = crud.file.get_all(conn)

    return files
