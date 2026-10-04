"""Cross-table reads over the tag hierarchy. Primarily for the FUSE mount.

A path here (e.g. "/genre/rock") is a sequence of tag names, matched
depth-by-depth against file_tag.parent_id edges. Root position isn't
enforced - a tag resolves wherever it occurs in the tree, regardless of
whether it's actually a root tag for any given file.
"""

from pathlib import Path

from tagumori import service
from tagumori.utils import flatten
from tagumori.vault import Vault, datacache


@datacache
def tag_names(vault: Vault) -> set[str]:
    return {t.name for t in vault.tags.get_all()}


@datacache
def resolve_path(vault: Vault, path: str) -> frozenset[int]:
    """The file_tag.id's matching path's full chain of segments exactly.

    Empty if any segment fails to match.
    """
    _, *parts = path.split("/")

    tuples = [(i, p) for i, p in enumerate(parts)]
    values_phs = ",".join("(?, ?)" for _ in tuples)

    values = tuple(flatten(tuples))

    result = vault.conn.execute(
        f"""
        WITH path(depth, tag_name) as (VALUES {values_phs}),

        cte as (
            SELECT
                file_tag.id id,
                0 depth
            FROM file_tag
            JOIN tag on tag.id = file_tag.tag_id
            JOIN path on path.depth = 0
            WHERE tag.name = path.tag_name

            UNION ALL

            SELECT
                child.id id,
                parent.depth + 1 depth
            FROM cte parent
            JOIN file_tag child on child.parent_id = parent.id
            JOIN tag ON tag.id = child.tag_id
            JOIN path on path.depth = parent.depth + 1
            WHERE tag.name = path.tag_name
        )

        SELECT distinct(id) from cte
        where depth = {len(parts) - 1}
    """,
        values,
    ).fetchall()

    return frozenset(r["id"] for r in result)


@datacache
def child_tags(vault: Vault, ids: frozenset[int]) -> list[str]:
    """Distinct tag names one level below given ids."""
    if not ids:
        return []

    phs = ",".join("?" for _ in ids)
    result = vault.conn.execute(
        f"""
        select distinct tag.name
        from file_tag
        join tag on tag.id = file_tag.tag_id
        and file_tag.parent_id in ({phs})
    """,
        tuple(ids),
    ).fetchall()

    return [r["name"] for r in result]


@datacache
def _files_by_name(vault: Vault, ids: frozenset[int]) -> dict[str, str]:

    if not ids:
        return {}

    phs = ",".join("?" for _ in ids)
    rows = vault.conn.execute(
        f"""select distinct(file.path) path from file
           join file_tag on file.id = file_tag.file_id
           where file_tag.id in ({phs})
        """,
        tuple(ids),
    ).fetchall()

    result = {Path(r["path"]).name: r["path"] for r in rows}

    return result


def files_at(vault: Vault, ids: frozenset[int]) -> list[str]:
    """Absolute paths of files tagged with given ids"""
    return list(_files_by_name(vault, ids).values())


def file_at(vault: Vault, ids: frozenset[int], name: str) -> str | None:
    """Absolute path of the file named `name` among those tagged with ids."""
    return _files_by_name(vault, ids).get(name)


@datacache
def query_names(vault: Vault) -> set[str]:
    return {q.name for q in vault.queries.get_all()}


@datacache
def _files_by_query(vault: Vault, name: str) -> dict[str, str]:
    """name -> path for every file a saved query resolves to.

    Empty if no query with this name exists.
    """
    query = vault.queries.get_by_name(name)
    if query is None:
        return {}

    files = service.execute_query(
        vault,
        query.select_tags,
        query.exclude_tags,
        query.ignore_tag_case,
        query.pattern,
        query.ignore_case,
        query.invert_match,
    )

    return {f.path.name: str(f.path) for f in files}


def files_for_query(vault: Vault, name: str) -> list[str]:
    """Absolute paths of files matched by the saved query `name`."""
    return list(_files_by_query(vault, name).values())


def file_for_query(vault: Vault, name: str, filename: str) -> str | None:
    """Absolute path of the file named `filename` within query `name`'s results."""
    return _files_by_query(vault, name).get(filename)
