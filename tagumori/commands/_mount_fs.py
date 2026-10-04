import errno
import stat
import sys
import time
from pathlib import Path

from fuse import FUSE, FuseOSError, Operations

from tagumori.reads import (
    _files_by_name,
    child_tags,
    file_at,
    file_for_query,
    files_for_query,
    query_names,
    resolve_path,
    tag_names,
)
from tagumori.vault import Vault


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

    def getattr(self, path: str, fh: int) -> dict:
        now = time.time()

        if path == "/":
            return _dir_attrs(now)

        self.vault.check_cache()

        root, *rest = path.split("/")[1:]

        if root == "tags":
            return self._tags_getattr(rest, now)
        if root == "queries":
            return self._queries_getattr(rest, now)

        raise FuseOSError(errno.ENOENT)

    def _tags_getattr(self, rest: list[str], now: float) -> dict:
        if not rest:
            return _dir_attrs(now)

        *init, last = rest

        if not init:
            # depth 1: only tag directories exist directly under /tags
            if last in tag_names(self.vault):
                return _dir_attrs(now)
            raise FuseOSError(errno.ENOENT)

        parent = "/" + "/".join(init)
        lookup_ids = resolve_path(self.vault, parent)

        if last in child_tags(self.vault, lookup_ids):
            return _dir_attrs(now)

        target = file_at(self.vault, lookup_ids, last)
        if target is not None:
            return _link_attrs(now, target)

        raise FuseOSError(errno.ENOENT)

    def _queries_getattr(self, rest: list[str], now: float) -> dict:
        if not rest:
            return _dir_attrs(now)

        if len(rest) == 1:
            (name,) = rest
            if name in query_names(self.vault):
                return _dir_attrs(now)
            raise FuseOSError(errno.ENOENT)

        if len(rest) == 2:
            name, filename = rest
            target = file_for_query(self.vault, name, filename)
            if target is not None:
                return _link_attrs(now, target)

        raise FuseOSError(errno.ENOENT)

    def readdir(self, path: str, fh: int) -> list[str | tuple]:
        now = time.time()

        if path == "/":
            return [".", "..", "tags", "queries"]

        self.vault.check_cache()

        root, *rest = path.split("/")[1:]

        if root == "tags":
            entries = self._tags_readdir(rest, now)
        elif root == "queries":
            entries = self._queries_readdir(rest, now)
        else:
            raise FuseOSError(errno.ENOENT)

        return [".", "..", *entries]

    def _tags_readdir(self, rest: list[str], now: float) -> list[tuple]:
        if not rest:
            tags = tag_names(self.vault)
            return [(name, _dir_attrs(now), 0) for name in tags]

        tag_path = "/" + "/".join(rest)
        lookup_ids = resolve_path(self.vault, tag_path)
        kids = child_tags(self.vault, lookup_ids)
        targets = _files_by_name(self.vault, lookup_ids)

        entries = [(name, _dir_attrs(now), 0) for name in kids]
        entries += [
            (Path(target).name, _link_attrs(now, target), 0)
            for target in targets.values()
        ]
        return entries

    def _queries_readdir(self, rest: list[str], now: float) -> list[tuple]:
        if not rest:
            names = query_names(self.vault)
            return [(name, _dir_attrs(now), 0) for name in names]

        (name,) = rest
        targets = files_for_query(self.vault, name)
        return [
            (Path(target).name, _link_attrs(now, target), 0) for target in targets
        ]

    def readlink(self, path: str) -> str:
        self.vault.check_cache()

        root, *rest = path.split("/")[1:]

        target = None
        if root == "tags":
            *init, last = rest
            parent = "/" + "/".join(init)
            lookup_ids = resolve_path(self.vault, parent)
            target = file_at(self.vault, lookup_ids, last)
        elif root == "queries":
            name, filename = rest
            target = file_for_query(self.vault, name, filename)

        if target is None:
            raise FuseOSError(errno.ENOENT)

        return target


if __name__ == "__main__":
    from tagumori.db.connect import get_connection

    vault = Vault(get_connection(Path("vault.db")))
    mountpoint = sys.argv[1]
    FUSE(TagumoriFS(vault), mountpoint, foreground=True)
