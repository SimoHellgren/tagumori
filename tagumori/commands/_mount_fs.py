import errno
import stat
import sys
import time
from pathlib import Path

from fuse import FUSE, FuseOSError, Operations

from tagumori.db.connect import get_connection
from tagumori.vault import Vault


def vault():
    return Vault(get_connection("vault.db"))


def resolve(conn, path):
    parts = path.split("/")

    _, first, *rest = parts

    start = conn.execute(
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
        kids = conn.execute(
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


def children(path):
    conn = vault().conn
    next_ids = resolve(conn, path)
    if not next_ids:
        return []

    phs = ",".join("?" for _ in next_ids)
    result = conn.execute(
        f"""
        select distinct tag.name
        from file_tag
        join tag on tag.id = file_tag.tag_id
        and file_tag.parent_id in ({phs})
    """,
        tuple(next_ids),
    ).fetchall()

    return [r["name"] for r in result]


def files(path):
    conn = vault().conn
    next_ids = resolve(conn, path)
    if not next_ids:
        return []

    phs = ",".join("?" for _ in next_ids)
    result = conn.execute(
        f"""select distinct(file.path) path from file
           join file_tag on file.id = file_tag.file_id
           where file_tag.id in ({phs})
        """,
        tuple(next_ids),
    ).fetchall()

    return [r["path"] for r in result]


def _dir_attrs(now):
    return {
        "st_mode": (stat.S_IFDIR | 0o755),
        "st_nlink": 2,
        "st_ctime": now,
        "st_mtime": now,
        "st_atime": now,
    }


def _link_attrs(now, target):
    return {
        "st_mode": (stat.S_IFLNK | 0o777),
        "st_nlink": 1,
        "st_size": len(target),
        "st_ctime": now,
        "st_mtime": now,
        "st_atime": now,
    }


class TagumoriFS(Operations):
    def __init__(self, vault: Vault):
        self.vault = vault

    def getattr(self, path, fh=None):
        now = time.time()

        if path == "/":
            return _dir_attrs(now)

        *init, last = path.split("/")
        parent = "/".join(init)

        if parent == "":
            # depth 1: only tag directories exist directly under root
            tags = [t.name for t in self.vault.tags.get_all()]
            if last in tags:
                return _dir_attrs(now)
            raise FuseOSError(errno.ENOENT)

        if last in children(parent):
            return _dir_attrs(now)

        target = next((p for p in files(parent) if Path(p).name == last), None)
        if target is not None:
            return _link_attrs(now, target)

        raise FuseOSError(errno.ENOENT)

    def readdir(self, path, fh):
        if path == "/":
            tags = [t.name for t in self.vault.tags.get_all()]
            return [".", "..", *tags]

        else:
            kids = children(path)
            paths = [Path(p).name for p in files(path)]
            return [".", "..", *kids, *paths]

    def readlink(self, path):
        *init, last = path.split("/")
        parent = "/".join(init)

        candidates = files(parent)
        target = next((p for p in candidates if Path(p).name == last), None)
        if target is None:
            raise FuseOSError(errno.ENOENT)

        return target


if __name__ == "__main__":
    mountpoint = sys.argv[1]
    FUSE(TagumoriFS(), mountpoint, foreground=True)
