"""Module for creating user-facing presentations"""

from collections.abc import Generator, Sequence
from pathlib import Path

import click

from tagumori.models import FileStatus, TaggedFile


def format_file_output(
    files: Sequence[TaggedFile], relative_to: Path, prefix: str
) -> Generator[str]:
    # TODO: the data flow / interface is a bit messy
    for file in files:
        try:
            # relative path
            display_path = prefix / file.path.relative_to(relative_to.resolve())

        except ValueError:
            # default to absolute path if not relative
            display_path = prefix / file.path

        msg = click.style(display_path, fg="green")

        # walrus protects from printin "None" when there are no tags
        if file.tags:
            msg += "\t" + click.style(file.tags, fg="cyan")

        yield msg


def print_box(title: str, lines: list[str]):
    """Prints a nice box around a title and lines"""
    width = max(len(click.unstyle(line)) for line in [title, *lines]) + 2

    click.echo(f"┌{'─' * width}┐")
    click.echo(f"│ {title.ljust(width - 1)}│")
    click.echo(f"├{'─' * width}┤")
    for line in lines:
        padding = width - 1 - len(click.unstyle(line))
        click.echo(f"│ {line}{' ' * padding}│")
    click.echo(f"└{'─' * width}┘")


def check_path(p: Path) -> dict:
    if p.exists():
        return {"text": "Exists", "fg": "green"}

    return {"text": "Not found", "fg": "red"}


# TODO: type for click.style arguments
def check_inode(file: TaggedFile) -> dict:
    status = file.file.status()
    return {
        FileStatus.OK: {"text": "OK", "fg": "green"},
        FileStatus.INODE_MISMATCH: {"text": "Mismatch", "fg": "red"},
        FileStatus.INODE_MISSING: {"text": "Inode missing", "fg": "yellow"},
        FileStatus.NOT_FOUND: {"text": "OK", "fg": "green"},  # handled by check_path
    }[status]


def print_file_info(file: TaggedFile) -> None:
    print_box(
        str(file.path),
        [
            f"Tags: {file.tags or ''}",
            "Path: " + click.style(**check_path(file.path)),
            "Inode/device: " + click.style(**check_inode(file)),
        ],
    )
