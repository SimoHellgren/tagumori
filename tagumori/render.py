"""Module for creating user-facing presentations"""

from collections.abc import Generator
from pathlib import Path

import click


def format_file_output(
    files: dict, long: bool, relative_to: Path, prefix: str
) -> Generator[str]:
    # TODO: the data flow / interface is a bit messy
    for path, data in files.items():
        try:
            # relative path
            display_path = prefix / path.relative_to(relative_to.resolve())

        except ValueError:
            # default to absolute path if not relative
            display_path = prefix / path

        msg = click.style(display_path, fg="green")

        # walrus protects from printin "None" when there are no tags
        if long and (ast := data["ast"]):
            msg += "\t" + click.style(ast, fg="cyan")

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
