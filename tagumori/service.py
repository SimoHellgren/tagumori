from collections import defaultdict
from collections.abc import Sequence
from itertools import groupby
from pathlib import Path
from sqlite3 import Connection, Row

from tagumori import crud
from tagumori.models import File, TaggedFile
from tagumori.query import parse_for_storage, search
from tagumori.query.ast import And, Expr, Tag
from tagumori.utils import compile_pattern


# utilities for turning the db file_tag structures to AST and paths
def _db_to_ast(file_tags: Sequence[Row]) -> Expr:
    """Turn db file_tag rows into an AST (with AND)"""
    nodes: dict[int, Tag] = {}
    children: dict[int, list[Tag]] = defaultdict(list)
    roots: list[Tag] = []

    for row in file_tags:
        tag = Tag(name=row["name"])
        nodes[row["id"]] = tag
        if row["parent_id"] is None:
            roots.append(tag)
        else:
            children[row["parent_id"]].append(tag)

    # wire up children
    for id_, tag in nodes.items():
        kids = children[id_]
        if len(kids) == 1:
            tag.children = kids[0]
        elif len(kids) > 1:
            tag.children = And(kids)

    if len(roots) == 1:
        return roots[0]
    return And(roots)


def _ast_to_paths(node: Expr, prefix=()) -> list[tuple[str, ...]]:
    match node:
        case Tag(name, None):
            return [prefix + (name,)]
        case Tag(name, children):
            return _ast_to_paths(children, prefix + (name,))
        case And(operands):
            return [p for op in operands for p in _ast_to_paths(op, prefix)]

        case _:
            return []


def _db_tags_to_paths(file_tags: Sequence[Row]) -> set[tuple[str, ...]]:
    return set(_ast_to_paths(_db_to_ast(file_tags)))


def attach_tree(
    conn: Connection, file_id: int, node: Expr, parent_id: int | None = None
):
    match node:
        case Tag(name, None):
            tag = crud.tag.get_or_create(conn, name)
            crud.file_tag.attach(conn, file_id, tag.id, parent_id)
        case Tag(name, children):
            tag = crud.tag.get_or_create(conn, name)
            filetag_id = crud.file_tag.attach(conn, file_id, tag.id, parent_id)
            attach_tree(conn, file_id, children, filetag_id)
        case And(operands):
            for op in operands:
                attach_tree(conn, file_id, op, parent_id)


def add_tags_to_files(
    conn: Connection,
    files: Sequence[Path],
    tags: Sequence[str],
    apply_tagalongs: bool = True,
):
    file_ids = [x.id for x in crud.file.get_or_create_many(conn, files)]

    tag_expr = ",".join(tags)
    node = parse_for_storage(tag_expr)

    for file_id in file_ids:
        attach_tree(conn, file_id, node)

    if apply_tagalongs:
        crud.tagalong.apply(
            conn,
            file_ids,
        )


def remove_tags_from_files(
    conn: Connection, files: Sequence[Path], tags: Sequence[str]
):
    # non-existing files are skipped here due to how get_many_by_path works.
    file_ids = [x.id for x in crud.file.get_many_by_path(conn, files)]

    tag_expr = ",".join(tags)
    node = parse_for_storage(tag_expr)

    tag_paths = _ast_to_paths(node)

    for file_id in file_ids:
        for tag in tags:
            for path in tag_paths:
                file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
                if file_tag_id:
                    crud.file_tag.detach(conn, file_tag_id)


def set_tags_on_files(
    conn: Connection, files: Sequence[Path], tags: Expr, apply_tagalongs: bool = True
):
    tag_expr = ",".join(tags)
    node = parse_for_storage(tag_expr)

    # remove unwanted paths
    desired_paths = set(_ast_to_paths(node))

    file_ids = [x.id for x in crud.file.get_or_create_many(conn, files)]

    db_tags = crud.file_tag.get_by_file_ids(conn, file_ids)

    lookup = {k: list(v) for k, v in groupby(db_tags, key=lambda x: x["file_id"])}

    for file_id in file_ids:
        existing_paths = _db_tags_to_paths(lookup.get(file_id, []))

        paths_to_delete = existing_paths - desired_paths
        for path in paths_to_delete:
            file_tag_id = crud.file_tag.resolve_path(conn, file_id, path)
            crud.file_tag.detach(conn, file_tag_id)

    # attach new tags - done after removal so new tagalongs aren't nuked.
    # add_tags_to_files evaluates ´tags´ as well, so there's a bit of double work here.
    add_tags_to_files(conn, files, tags, apply_tagalongs)


def drop_file_tags(conn: Connection, files: Sequence[Path], retain_file: bool = False):
    file_ids = [x.id for x in crud.file.get_many_by_path(conn, files)]
    for file_id in file_ids:
        crud.file_tag.drop_for_file(conn, file_id)

        if not retain_file:
            crud.file.delete(conn, file_id)


def lookup_tags(conn: Connection, files: Sequence[File]) -> list[TaggedFile]:
    ids = [file.id for file in files]
    tags = crud.file_tag.get_by_file_ids(conn, ids)

    # tags are ordered by file id so we can groupby safely
    lookup = {k: list(v) for k, v in groupby(tags, key=lambda x: x["file_id"])}

    return [TaggedFile(f, _db_to_ast(lookup.get(f.id, []))) for f in files]


def list_files(
    conn: Connection,
    select: Sequence[str],
    exclude: Sequence[str],
    ignore_tag_case: bool,
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
    long: bool,
) -> list[TaggedFile]:
    files = execute_query(
        conn, select, exclude, ignore_tag_case, pattern, ignore_case, invert_match
    )

    if long:
        files_with_tags = lookup_tags(conn, files)
    else:
        files_with_tags = [TaggedFile(f, None) for f in files]

    return files_with_tags


def execute_query(
    conn: Connection,
    select_strs: Sequence[str],
    exclude_strs: Sequence[str],
    ignore_tag_case: bool = False,
    pattern: str = ".*",
    ignore_case: bool = False,
    invert_match: bool = False,
) -> list[File]:

    query_parts = []

    if select_strs:
        query_parts.append("|".join(select_strs))

    if exclude_strs:
        query_parts.append("|".join(f"!{e}" for e in exclude_strs))

    query_str = ",".join(query_parts)

    if query_str:
        # pass lambdafunc to let dependent funcs to get file ids lazily
        ids = search(
            conn,
            query_str,
            lambda: {x.id for x in crud.file.get_all(conn)},
            not ignore_tag_case,
        )
        files = crud.file.get_many(conn, list(ids))
    else:
        files = crud.file.get_all(conn)

    regex = compile_pattern(pattern, ignore_case)

    return sorted(
        (f for f in files if bool(regex.search(str(f.path))) ^ invert_match),
        key=lambda f: f.path,
    )


def relocate_file(conn: Connection, file: File, search_root: Path) -> None:
    """Finds a file by inode/device and updates its path."""
    target_inode = file.inode
    target_device = file.device

    for path in search_root.rglob("*"):
        if not path.is_file():
            continue

        stat = path.stat()

        if stat.st_ino == target_inode and stat.st_dev == target_device:
            crud.file.update(conn, file.id, path, stat.st_ino, stat.st_dev)
