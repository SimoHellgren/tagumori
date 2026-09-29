from collections import defaultdict
from collections.abc import Sequence
from itertools import groupby
from pathlib import Path
from sqlite3 import Connection

from tagumori import crud
from tagumori.models import File, FileTagNode, TagalongNames, TaggedFile
from tagumori.query import search
from tagumori.query.ast import And, Expr, Not, Tag, and_
from tagumori.utils import compile_matcher, flatten


# utilities for turning the db file_tag structures to AST and paths
def _db_to_ast(file_tags: Sequence[FileTagNode]) -> Expr:
    """Turn db file_tag rows into an AST (with AND)"""
    nodes: dict[int, Tag] = {}
    children: dict[int, list[Expr]] = defaultdict(list)
    roots: list[Expr] = []

    for row in file_tags:
        tag = Tag(name=row.tag_name)
        nodes[row.id] = tag
        if row.parent_id is None:
            roots.append(tag)
        else:
            children[row.parent_id].append(tag)

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


def _paths_by_id(rows: Sequence[FileTagNode]) -> dict[int, tuple[str, ...]]:
    names = {row.id: row.tag_name for row in rows}
    children: dict[int | None, list[int]] = defaultdict(list)

    for row in rows:
        children[row.parent_id].append(row.id)

    paths: dict[int, tuple[str, ...]] = {}

    def visit(node_id: int, parent_path: tuple[str, ...]) -> None:
        path = parent_path + (names[node_id],)
        paths[node_id] = path
        for child_id in children[node_id]:
            visit(child_id, path)

    for root_id in children[None]:
        visit(root_id, ())

    return paths


# TODO: could use a dedicated return type
def _ast_to_leaf_paths(node: Expr, prefix=()) -> set[tuple[str, ...]]:
    """Takes an AST and returns a list of all paths from root to leaf.
    e.g. a[b,c[d]] -> [(a,b), (a,c,d)]
    """
    match node:
        case Tag(name, None):
            return {prefix + (name,)}
        case Tag(name, children):
            assert children is not None  # for mypy
            return _ast_to_leaf_paths(children, prefix + (name,))
        case And(operands):
            return {p for op in operands for p in _ast_to_leaf_paths(op, prefix)}

        case _:
            return set()


def _ast_to_path_closure(node: Expr, prefix=()) -> set[tuple[str, ...]]:
    """Takes an AST and returns paths from root to each child.
    e.g. a[b,c[d]] -> {(a,), (a,b), (a,c), (a,c,d)}
    """
    match node:
        case Tag(name, None):
            return {prefix + (name,)}
        case Tag(name, children):
            assert children is not None  # for mypy
            here = prefix + (name,)
            return {here} | _ast_to_path_closure(children, here)
        case And(operands):
            return set(flatten(_ast_to_path_closure(op, prefix) for op in operands))

        case _:
            return set()


# TODO: consider removing
def _db_tags_to_leaf_paths(file_tags: Sequence[FileTagNode]) -> set[tuple[str, ...]]:
    """Leaf paths only - see _paths_by_id for every node's materialized path."""
    return set(_ast_to_leaf_paths(_db_to_ast(file_tags)))


def attach_tree(
    conn: Connection, file_id: int, node: Expr, parent_id: int | None = None
):
    match node:
        case Tag(name, None):
            tag = crud.tag.get_or_create(conn, name)
            crud.file_tag.attach(conn, file_id, tag.id, parent_id)
        case Tag(name, children):
            assert children is not None  # for mypy
            tag = crud.tag.get_or_create(conn, name)
            filetag_id = crud.file_tag.attach(conn, file_id, tag.id, parent_id)
            attach_tree(conn, file_id, children, filetag_id)
        case And(operands):
            for op in operands:
                attach_tree(conn, file_id, op, parent_id)


def add_tags_to_files(
    conn: Connection,
    files: Sequence[Path],
    tags: Expr,
    apply_tagalongs: bool = True,
):
    file_ids = [x.id for x in crud.file.get_or_create_many(conn, files)]

    for file_id in file_ids:
        attach_tree(conn, file_id, tags)

    if apply_tagalongs:
        crud.tagalong.apply(
            conn,
            file_ids,
        )


def get_file_tag_nodes(conn: Connection, file_ids: list[int]) -> list[FileTagNode]:
    if not file_ids:
        return []

    placeholders = ",".join("?" for _ in file_ids)
    q = f"""
        SELECT
            file_tag.file_id,
            file_tag.id,
            tag.name tag_name,
            file_tag.parent_id
        FROM file_tag
        JOIN tag
            on tag.id = file_tag.tag_id
        WHERE file_tag.file_id IN ({placeholders})
        ORDER BY file_id, parent_id, name
    """
    return [FileTagNode(**row) for row in conn.execute(q, file_ids).fetchall()]


def remove_tags_from_files(conn: Connection, files: Sequence[Path], tags: Expr):

    # remove only leafs
    unwanted = set(_ast_to_leaf_paths(tags))

    # fetch files and their tags
    file_ids = [x.id for x in crud.file.get_or_create_many(conn, files)]
    db_tags = get_file_tag_nodes(conn, file_ids)

    existing_paths = _paths_by_id(db_tags)

    for ft_id, path in existing_paths.items():
        if path in unwanted:
            crud.file_tag.detach(conn, ft_id)


def set_tags_on_files(
    conn: Connection,
    files: Sequence[Path],
    tags: Expr,
    apply_tagalongs: bool = True,
):
    # get closure of tags/paths to retain
    keep = _ast_to_path_closure(tags)

    # fetch files and their tags
    file_ids = [x.id for x in crud.file.get_or_create_many(conn, files)]
    db_tags = get_file_tag_nodes(conn, file_ids)

    # materialized path to every node, keyed by file_tag id
    existing_paths = _paths_by_id(db_tags)

    for ft_id, path in existing_paths.items():
        # removes a filetag if it is not in the "keep" list AND
        # - it is a root (cascades) OR
        # - its parent shall be kept, i.e. this is the topmost
        #   node to delete in its branch
        if path not in keep and (len(path) == 1 or path[:-1] in keep):
            crud.file_tag.detach(conn, ft_id)

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
    tags = get_file_tag_nodes(conn, ids)

    # tags are ordered by file id so we can groupby safely
    lookup = {k: list(v) for k, v in groupby(tags, key=lambda x: x.file_id)}

    return [TaggedFile(f, _db_to_ast(lookup.get(f.id, []))) for f in files]


def list_files(
    conn: Connection,
    select: Expr | None,
    exclude: Expr | None,
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
    select: Expr | None,
    exclude: Expr | None,
    ignore_tag_case: bool = False,
    pattern: str = ".*",
    ignore_case: bool = False,
    invert_match: bool = False,
) -> list[File]:

    negated_exclude = Not(exclude) if exclude is not None else None
    query_expr = and_(*[x for x in [select, negated_exclude] if x is not None])

    if query_expr:
        # pass lambdafunc to let dependent funcs to get file ids lazily
        ids = search(
            conn,
            query_expr,
            lambda: {x.id for x in crud.file.get_all(conn)},
            not ignore_tag_case,
        )
        files = crud.file.get_many(conn, list(ids))
    else:
        files = crud.file.get_all(conn)

    matcher = compile_matcher(pattern, ignore_case, invert_match)

    return sorted(
        filter(lambda f: matcher(str(f.path)), files),
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


def list_tagalong_names(conn: Connection) -> list[TagalongNames]:
    result = conn.execute("""
        SELECT
            t.name tag_name, 
            ta.name tagalong_name
        FROM tagalong
        JOIN tag t on tagalong.tag_id = t.id
        JOIN tag ta on tagalong.tagalong_id = ta.id
        ORDER BY t.name, ta.name
        """).fetchall()

    return [TagalongNames(row["tag_name"], row["tagalong_name"]) for row in result]
