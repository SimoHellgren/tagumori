import re
from itertools import chain, islice
from pathlib import Path
from typing import Generator, Iterator

import click

flatten = chain.from_iterable
find = lambda f, it, d=None: next(filter(f, it), d)


def drop(it: Iterator, n: int):
    return islice(it, n, None)


def tail(it: Iterator):
    return drop(it, 1)


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

        if long:
            roots = data["roots"]
            msg += "\t" + click.style(",".join(str(root) for root in roots), fg="cyan")

        yield msg
