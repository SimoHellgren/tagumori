"""Holds functions / logic for discovering vaults."""

import os
from pathlib import Path

import click

POINTER = Path(".tagumori") / "pointer"


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"

    return Path(base) / "tagumori"


def vault_db_path(vault_id: str) -> Path:
    if Path(vault_id).name != vault_id:
        raise click.ClickException(f"Invalid vault id in pointer: {vault_id}")

    return data_dir() / vault_id / "vault.db"


def new_db_dir() -> Path:
    """Creates and returns an empty directory for a new vault's db.

    The id is random; `mkdir` is the collision check, so it can't race.
    """
    import secrets

    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    while True:
        candidate = root / f"tagumori-{secrets.token_hex(3)}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate


def pointer_path(directory: Path) -> Path:
    return directory / POINTER


def read_pointer(pointer: Path) -> str | None:
    if not pointer.is_file():
        return None

    return pointer.read_text().strip() or None


def discover_vault(start: Path | None = None) -> Path | None:
    start = start or Path.cwd()
    for directory in [start, *start.parents]:
        vault_id = read_pointer(pointer_path(directory))
        if vault_id:
            return vault_db_path(vault_id)

    return None
