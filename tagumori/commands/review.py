import sys
from pathlib import Path
from typing import TextIO

import click

from tagumori import service
from tagumori.commands.context import LazyVault
from tagumori.query import parse_for_storage
from tagumori.render import print_file_info
from tagumori.utils import flatten
from tagumori.vault import Vault


class ReviewSession:
    def __init__(self, vault: Vault, items: list[Path]):
        self.vault = vault
        self.items = items
        self.index = 0

        self.known_tags = {t.name for t in vault.tags.get_all()}

    @property
    def current(self) -> Path:
        return self.items[self.index]

    def next(self) -> None:
        self.index = min(self.index + 1, len(self.items) - 1)

    def prev(self) -> None:
        self.index = max(0, self.index - 1)

    def goto(self, index: int) -> None:
        if not 0 <= index <= len(self.items) - 1:
            click.echo("Index not in range")
            return

        self.index = index

    def file_info(self) -> None:

        file = self.vault.files.get_by_path(self.current)

        if not file:
            click.echo("File not in vault")
            return

        tagged_file = service.lookup_tags(self.vault, [file])

        print_file_info(tagged_file[0])

    def add_tags(self, expr: str) -> None:
        # validate before hitting db
        node = parse_for_storage(expr)

        service.add_tags_to_files(self.vault, [self.current], node)

        # TODO: should probably make _ast_to_leaf_paths a public method
        # TODO: paths is also a bit overkill - could just recurse to get unique tags
        new_tags = {*flatten(service._ast_to_leaf_paths(node))}
        self.known_tags |= new_tags


def _stdio_has_tty() -> bool:
    """True if a human could plausibly be typing at stdin, stdout, or stderr."""
    return any(s.isatty() for s in (sys.stdin, sys.stdout, sys.stderr))


@click.command()
@click.argument("file", type=click.File("r"))
@click.pass_obj
def review(lazy_vault: LazyVault, file: TextIO):
    from tagumori.commands._review_tui import REPL

    lines = [Path(l.strip()) for l in file if l.strip()]

    if not lines:
        click.echo("Input file is empty.")
        return

    if not _stdio_has_tty():
        raise click.ClickException(
            "review needs an interactive terminal; none of stdin/stdout/stderr is one."
        )

    with lazy_vault as vault:
        session = ReviewSession(vault, lines)

    repl = REPL(session)

    repl.run()
