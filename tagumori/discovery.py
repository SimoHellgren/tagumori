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
