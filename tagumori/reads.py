"""Cross-table reads over the tag hierarchy. Primarily for the FUSE mount.

A path here (e.g. "/genre/rock") is a sequence of tag names, matched
depth-by-depth against file_tag.parent_id edges. Root position isn't
enforced - a tag resolves wherever it occurs in the tree, regardless of
whether it's actually a root tag for any given file.
"""

from pathlib import Path

from tagumori.vault import Vault, datacache


@datacache
def tag_names(vault: Vault) -> set[str]:
    return {t.name for t in vault.tags.get_all()}


@datacache
def resolve_path(vault: Vault, path: str) -> frozenset[int]:
    """The file_tag.id's matching path's full chain of segments exactly.

    Empty if any segment fails to match.
    """

    parts = path.split("/")

    _, first, *rest = parts

    start = vault.conn.execute(
        """
        select file_tag.id from file_tag
        join tag on tag.id = file_tag.tag_id
        where tag.name = ?
        """,
        (first,),
    ).fetchall()

    next_ids = {r["id"] for r in start}

    for part in rest:
        phs = ",".join("?" for _ in next_ids)
        # find child tags
        kids = vault.conn.execute(
            f"""select
                file_tag.id,
                tag.name
            from file_tag
            join tag on tag.id = file_tag.tag_id
            where tag.name = ?
            and file_tag.parent_id in ({phs})
            """,
            (part, *next_ids),
        ).fetchall()

        if not kids:
            return frozenset()

        next_ids = {r["id"] for r in kids}

    result = frozenset(next_ids)
    return result


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
