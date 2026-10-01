import errno
import stat
import sys
import time
from pathlib import Path

from fuse import FUSE, FuseOSError, Operations

from tagumori.reads import _files_by_name, child_tags, file_at, resolve_path, tag_names
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

        *init, last = path.split("/")
        parent = "/".join(init)

        if parent == "":
            # depth 1: only tag directories exist directly under root
            tags = tag_names(self.vault)
            if last in tags:
                return _dir_attrs(now)
            raise FuseOSError(errno.ENOENT)

        lookup_ids = resolve_path(self.vault, parent)

        if last in child_tags(self.vault, lookup_ids):
            return _dir_attrs(now)

        target = file_at(self.vault, lookup_ids, last)
        if target is not None:
            return _link_attrs(now, target)

        raise FuseOSError(errno.ENOENT)

    def readdir(self, path: str, fh: int) -> list[str | tuple]:
        now = time.time()
        if path == "/":
            tags = tag_names(self.vault)
            entries = [(name, _dir_attrs(now), 0) for name in tags]

        else:
            lookup_ids = resolve_path(self.vault, path)
            kids = child_tags(self.vault, lookup_ids)
            targets = _files_by_name(self.vault, lookup_ids)

            entries = [(name, _dir_attrs(now), 0) for name in kids]

            entries += [
                (Path(target).name, _link_attrs(now, target), 0)
                for target in targets.values()
            ]

        return [".", "..", *entries]

    def readlink(self, path: str) -> str:
        *init, last = path.split("/")
        parent = "/".join(init)

        lookup_ids = resolve_path(self.vault, parent)

        target = file_at(self.vault, lookup_ids, last)
        if target is None:
            raise FuseOSError(errno.ENOENT)

        return target


if __name__ == "__main__":
    from tagumori.db.connect import get_connection

    vault = Vault(get_connection(Path("vault.db")))
    mountpoint = sys.argv[1]
    FUSE(TagumoriFS(vault), mountpoint, foreground=True)
