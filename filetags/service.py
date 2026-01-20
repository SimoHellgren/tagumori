from pathlib import Path
from sqlite3 import Connection, Row

from filetags import crud
from filetags.models.node import Node
from filetags.utils import flatten


def attach_tree(
    conn: Connection, file_id: int, node: Node, parent_id: int | None = None
):
    tag = crud.tag.get_or_create(conn, node.value)
    filetag_id = crud.file_tag.attach(conn, file_id, tag["id"], parent_id)
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


def build_tree(file_tags: list) -> list[Node]:
    roots: list[Node] = []
    nodes: dict[str | None, Node] = {}

    # construct nodes
    for id_, tag, parent_id in file_tags:
        nodes[id_] = Node(value=tag)

    # add children & record root nodes
    for id_, _, parent_id in file_tags:
        node = nodes[id_]
        if parent_id is None:
            roots.append(node)
        else:
            nodes[parent_id].add_child(node)

    return roots


def set_tags_on_files(
    conn: Connection, files: list[Path], tag: Node, apply_tagalongs: bool = True
):
    # remove unwanted paths
    _, *nodes = tag.preorder()
    desired_paths = set(tuple(n.path()[1:]) for n in nodes)

    file_ids = [x["id"] for x in crud.file.get_or_create_many(conn, files)]

    for file_id in file_ids:
        tags = crud.file_tag.get_by_file_id(conn, file_id)

        roots = build_tree(tags)
        db_nodes = flatten(n.preorder() for n in roots)
        existing_paths = set(n.path() for n in db_nodes)

        paths_to_delete = existing_paths - desired_paths
        for path in paths_to_delete:
            file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
            crud.file_tag.detach(conn, file_tag_id)

    # attach new tags - done after removal so new tagalongs aren't nuked.
    add_tags_to_files(conn, files, tag.children, apply_tagalongs)


def drop_file_tags(conn: Connection, files: list[Path], retain_file: bool = False):
    file_ids = [x["id"] for x in crud.file.get_many_by_path(conn, files)]
    for file_id in file_ids:
        crud.file_tag.drop_for_file(conn, file_id)

        if not retain_file:
            crud.file.delete(conn, file_id)


def get_files_with_tags(conn: Connection, files: list[Path]) -> dict[Path, list[Node]]:
    # TODO: turn into a proper batch get
    file_records = crud.file.get_many_by_path(conn, files)
    paths = [Path(f["path"]) for f in file_records]
    tags = [crud.file_tag.get_by_file_id(conn, file["id"]) for file in file_records]
    roots = [build_tree(tag) for tag in tags]

    return dict(zip(paths, roots))


def _find_files_matching_all_paths(conn: Connection, node: Node) -> set[int]:
    matches = []
    for _, *p in node.paths_down():
        file_ids = {x["file_id"] for x in crud.file_tag.find_all(conn, p)}
        matches.append(file_ids)

    return set.intersection(*matches)


def search_files(conn: Connection, select_tags: list[Node], exclude_tags: list[Node]):
    if select_tags:
        include_ids = set.union(
            set(), *(_find_files_matching_all_paths(conn, n) for n in select_tags)
        )
    else:
        # fallback to all ids if no select_tags provided
        # TODO: when grammar gets improved, could just default to -s "*" in the cli instead.
        include_ids = set(x["id"] for x in crud.file.get_all(conn))

    exclude_ids = set.union(
        set(), *(_find_files_matching_all_paths(conn, n) for n in exclude_tags)
    )

    ids = tuple(include_ids - exclude_ids)

    files = crud.file.get_many(conn, ids)

    return sorted(files, key=lambda x: x["path"])


def get_all_files(conn: Connection) -> list[Row]:
    files = crud.file.get_all(conn)
    return sorted(files, key=lambda x: x["path"])
