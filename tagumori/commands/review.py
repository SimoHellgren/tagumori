import cmd
from itertools import chain
from pathlib import Path
from typing import TextIO

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document

from tagumori import crud, service
from tagumori.commands.context import LazyVault
from tagumori.query import parse_for_storage

flatten = chain.from_iterable


class ReviewSession:
    def __init__(self, vault: LazyVault, items: list[Path]):
        self.vault = vault
        self.items = items
        self.index = 0

        with vault as conn:
            self.known_tags = {t.name for t in crud.tag.get_all(conn)}

    @property
    def current(self) -> Path:
        return self.items[self.index]

    def next(self) -> None:
        self.index = min(self.index + 1, len(self.items) - 1)

    def prev(self) -> None:
        self.index = max(0, self.index - 1)

    def goto(self, index: int) -> None:
        if not 0 <= index <= len(self.items) - 1:
            print("Index not in range")
            return

        self.index = index

    def add_tags(self, expr: str) -> None:
        # validate before hitting db
        node = parse_for_storage(expr)

        with self.vault as conn:
            service.add_tags_to_files(conn, [self.current], [expr])

        # TODO: should probably make _ast_to_paths a public method
        new_tags = {*flatten(service._ast_to_paths(node))}
        self.known_tags |= new_tags


DELIMS = "[,"


class TagCompleter(Completer):
    # TODO: consider persisting to FileHistory (see prompt_toolkit docs)
    # this should be a github issue, though

    """Completer for `tag[child,child[grandchild]]`-style expressions."""

    def __init__(self, known_tags: set[str]):
        self.known_tags = known_tags

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        cut = max(text.rfind(d) for d in DELIMS)

        partial = text[cut + 1 :].lstrip()

        # TODO: consider case-insensitive completions
        for tag in sorted(t for t in self.known_tags if t.startswith(partial)):
            yield Completion(tag, start_position=-len(partial))

        # TODO: completions for at least ], perhaps [
        # char_before_token = text[token_start - 1] if token_start > 0 else ""
        # depth = text.count("[") - text.count("]")
        # last_char = text[-1] if text else ""

        # if depth > 0 and last_char != ",":
        #     yield Completion("]", start_position=0, display_meta="close group")

        # if char_before_token in ("[", ",", ""):
        #     for tag in sorted(self.get_tags()):
        #         if tag.startswith(partial):


# TODO: autorun file info when cursor moves
class REPL(cmd.Cmd):
    prompt = "> "

    def __init__(self, session: ReviewSession):
        self.session = session
        self.pt: PromptSession = PromptSession()
        self.completer = TagCompleter(session.known_tags)

        super().__init__()

    def _prompt(self):
        s = self.session
        return f"{(s.index + 1)} / {len(s.items)} {s.current.name} > "

    def run(self):
        # TODO: move elsewhere, perhaps init
        commands = [k.removeprefix("do_") for k in vars(REPL) if k.startswith("do_")]
        completer = WordCompleter(sorted([*commands, "help"]))
        while True:
            try:
                line = self.pt.prompt(self._prompt(), completer=completer)
            except (EOFError, KeyboardInterrupt):
                break
            if self.onecmd(line):
                break

    def do_goto(self, arg):
        """Go to position (indexed from 1)"""
        try:
            position = int(arg)
        except ValueError:
            print(f"'{arg}' is not an integer")
            return

        self.session.goto(position - 1)

    def do_prev(self, arg):
        """Go back"""
        self.session.prev()

    def do_next(self, arg):
        """Move along"""
        self.session.next()

    def emptyline(self):
        """Equivalent to do_next"""
        self.do_next(None)

    def do_exit(self, arg):
        """Exit the REPL"""
        return True

    def do_EOF(self, arg):
        """Exit the REPL"""
        print()
        return True

    def do_add(self, arg):
        result = self.pt.prompt("Add tags: ", completer=self.completer)

        self.session.add_tags(result)

        print(result)


@click.command()
@click.argument("file", type=click.File("r"))
@click.pass_obj
def review(vault: LazyVault, file: TextIO):
    lines = [Path(l.strip()) for l in file]

    # TODO: still bug when reading from stdin

    session = ReviewSession(vault, lines)

    repl = REPL(session)

    repl.run()
