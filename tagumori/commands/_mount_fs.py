import errno
import stat
import sys
import time
from pathlib import Path

from fuse import FUSE, FuseOSError, Operations

from tagumori.reads import children, files
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

        if last in children(self.vault, parent):
            return _dir_attrs(now)

        target = next(
            (p for p in files(self.vault, parent) if Path(p).name == last), None
        )
        if target is not None:
            return _link_attrs(now, target)

        raise FuseOSError(errno.ENOENT)

    def readdir(self, path, fh):
        if path == "/":
            tags = [t.name for t in self.vault.tags.get_all()]
            return [".", "..", *tags]

        else:
            kids = children(self.vault, path)
            paths = [Path(p).name for p in files(self.vault, path)]
            return [".", "..", *kids, *paths]

    def readlink(self, path):
        *init, last = path.split("/")
        parent = "/".join(init)

        candidates = files(self.vault, parent)
        target = next((p for p in candidates if Path(p).name == last), None)
        if target is None:
            raise FuseOSError(errno.ENOENT)

        return target


if __name__ == "__main__":
    from tagumori.db.connect import get_connection

    vault = Vault(get_connection(Path("vault.db")))
    mountpoint = sys.argv[1]
    FUSE(TagumoriFS(vault), mountpoint, foreground=True)
