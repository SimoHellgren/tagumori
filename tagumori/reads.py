"""Cross-table reads over the tag hierarchy. Primarily for the FUSE mount.

A path here (e.g. "/genre/rock") is a sequence of tag names, matched
depth-by-depth against file_tag.parent_id edges. Root position isn't
enforced - a tag resolves wherever it occurs in the tree, regardless of
whether it's actually a root tag for any given file.
"""

from tagumori.vault import Vault


def resolve_path(vault: Vault, path: str) -> set[int]:
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
            f"""
            with names as (
                select
                    file_tag.id,
                    file_tag.parent_id,
                    tag.name
                from file_tag
                join tag on tag.id = file_tag.tag_id

            )

            select
                child.id,
                child.name
            from names parent
            join names child on child.parent_id = parent.id
            where child.name = ?
            and parent.id in ({phs})
            """,
            (part, *next_ids),
        ).fetchall()

        if not kids:
            return set()

        next_ids = {r["id"] for r in kids}

    return next_ids


def child_tags(vault: Vault, path: str) -> list[str]:
    """Distinct tag names one level below wherever `path` resolves to."""
    next_ids = resolve_path(vault, path)
    if not next_ids:
        return []

    phs = ",".join("?" for _ in next_ids)
    result = vault.conn.execute(
        f"""
        select distinct tag.name
        from file_tag
        join tag on tag.id = file_tag.tag_id
        and file_tag.parent_id in ({phs})
    """,
        tuple(next_ids),
    ).fetchall()

    return [r["name"] for r in result]


def files_at(vault: Vault, path: str) -> list[str]:
    """Absolute paths of files tagged exactly at wherever `path` resolves to."""

    next_ids = resolve_path(vault, path)
    if not next_ids:
        return []

    phs = ",".join("?" for _ in next_ids)
    result = vault.conn.execute(
        f"""select distinct(file.path) path from file
           join file_tag on file.id = file_tag.file_id
           where file_tag.id in ({phs})
        """,
        tuple(next_ids),
    ).fetchall()

    return [r["path"] for r in result]
