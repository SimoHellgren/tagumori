from tagumori.vault import Vault


def resolve(vault: Vault, path: str):
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


def children(vault: Vault, path: str):
    next_ids = resolve(vault, path)
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


def files(vault: Vault, path: str):
    next_ids = resolve(vault, path)
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
