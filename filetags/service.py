from collections import defaultdict
from pathlib import Path
from sqlite3 import Connection, Row

from filetags import crud
from filetags.models.node import Node
from filetags.query import parse_for_storage, search
from filetags.query.ast import And, Expr, Tag
from filetags.utils import compile_pattern


def attach_tree(
    conn: Connection, file_id: int, node: Expr, parent_id: int | None = None
):
    match node:
        case Tag(name, None):
            tag = crud.tag.get_or_create(conn, name)
            crud.file_tag.attach(conn, file_id, tag["id"], parent_id)
        case Tag(name, children):
            tag = crud.tag.get_or_create(conn, name)
            filetag_id = crud.file_tag.attach(conn, file_id, tag["id"], parent_id)
            attach_tree(conn, file_id, children, filetag_id)
        case And(operands):
            for op in operands:
                attach_tree(conn, file_id, op, parent_id)


def add_tags_to_files(
    conn: Connection, files: list[Path], tags: list[str], apply_tagalongs: bool = True
):
    file_ids = [x["id"] for x in crud.file.get_or_create_many(conn, files)]

    tag_expr = ",".join(tags)
    node = parse_for_storage(tag_expr)

    for file_id in file_ids:
        attach_tree(conn, file_id, node)

    if apply_tagalongs:
        crud.tagalong.apply(
            conn,
            file_ids,
        )


def _ast_to_paths(node: Expr, prefix=()) -> list[tuple[str, ...]]:
    match node:
        case Tag(name, None):
            return [prefix + (name,)]
        case Tag(name, children):
            return _ast_to_paths(children, prefix + (name,))
        case And(operands):
            return [p for op in operands for p in _ast_to_paths(op, prefix)]


def remove_tags_from_files(conn: Connection, files: list[Path], tags: list[str]):
    # non-existing files are skipped here due to how get_many_by_path works.
    file_ids = [x["id"] for x in crud.file.get_many_by_path(conn, files)]

    tag_expr = ",".join(tags)
    node = parse_for_storage(tag_expr)

    tag_paths = _ast_to_paths(node)

    for file_id in file_ids:
        for tag in tags:
            for path in tag_paths:
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


def _db_tags_to_paths(file_tags: list[Row]) -> set[tuple[str, ...]]:
    roots = []
    children = defaultdict(list)

    for row in file_tags:
        parent = row["parent_id"]
        target = roots if parent is None else children[parent]
        target.append(row)

    paths = []

    def walk(row, prefix):
        path = prefix + (row["name"],)
        kids = children[row["id"]]
        if not kids:
            paths.append(path)
        else:
            for kid in kids:
                walk(kid, path)

    for root in roots:
        walk(root, ())

    return set(paths)


def set_tags_on_files(
    conn: Connection, files: list[Path], tags: Expr, apply_tagalongs: bool = True
):
    tag_expr = ",".join(tags)
    node = parse_for_storage(tag_expr)

    # remove unwanted paths
    desired_paths = set(_ast_to_paths(node))

    file_ids = [x["id"] for x in crud.file.get_or_create_many(conn, files)]

    for file_id in file_ids:
        db_tags = crud.file_tag.get_by_file_id(conn, file_id)

        existing_paths = _db_tags_to_paths(db_tags)

        paths_to_delete = existing_paths - desired_paths
        for path in paths_to_delete:
            file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
            crud.file_tag.detach(conn, file_tag_id)

    # attach new tags - done after removal so new tagalongs aren't nuked.
    # add_tags_to_files evaluates ´tags´ as well, so there's a bit of double work here.
    add_tags_to_files(conn, files, tags, apply_tagalongs)


def drop_file_tags(conn: Connection, files: list[Path], retain_file: bool = False):
    file_ids = [x["id"] for x in crud.file.get_many_by_path(conn, files)]
    for file_id in file_ids:
        crud.file_tag.drop_for_file(conn, file_id)

        if not retain_file:
            crud.file.delete(conn, file_id)


def get_files_with_tags(conn: Connection, files: list[Path]) -> dict[Path, list[Node]]:
    # TODO: turn into a proper batch get
    file_records = crud.file.get_many_by_path(conn, files)
    tags = [crud.file_tag.get_by_file_id(conn, file["id"]) for file in file_records]
    roots = [build_tree(tag) for tag in tags]

    return {
        Path(f["path"]): {"file": f, "roots": r} for f, r in zip(file_records, roots)
    }


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


def execute_query(
    conn: Connection,
    select_strs: list[str],
    exclude_strs: list[str],
    pattern: str = ".*",
    ignore_case: bool = False,
    invert_match: bool = False,
) -> list[Path]:

    selects = "|".join(select_strs)
    excludes = "|".join(exclude_strs)

    query_str = selects + (f",!{excludes}" if excludes else "")

    if query_str:
        ids = search(conn, query_str, True)
        files = crud.file.get_many(conn, list(ids))
    else:
        files = crud.file.get_all(conn)

    regex = compile_pattern(pattern, ignore_case)

    return [
        Path(f["path"]) for f in files if bool(regex.search(f["path"])) ^ invert_match
    ]


def get_all_files(conn: Connection) -> list[Row]:
    files = crud.file.get_all(conn)
    return sorted(files, key=lambda x: x["path"])


def relocate_file(conn: Connection, file: Row, search_root: Path):
    """Finds a file by inode/device and updates its path."""
    target_inode = file["inode"]
    target_device = file["device"]

    for path in search_root.rglob("*"):
        if not path.is_file():
            continue

        stat = path.stat()

        if stat.st_ino == target_inode and stat.st_dev == target_device:
            crud.file.update(conn, file["id"], path, stat.st_ino, stat.st_dev)
