import re
from itertools import chain
from pathlib import Path
from typing import Generator

import click

flatten = chain.from_iterable


def compile_pattern(pattern: str, ignore_case: bool):
    if not pattern:
        return None

    flags = re.IGNORECASE if ignore_case else 0

    return re.compile(pattern, flags)


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
