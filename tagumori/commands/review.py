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
from tagumori.query.parser import UnexpectedCharacters, UnexpectedToken
from tagumori.render import print_file_info

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

    def file_info(self) -> None:
        with self.vault as conn:
            file = crud.file.get_by_path(conn, self.current)

            if not file:
                print("File not in vault")
                return

            tagged_file = service.lookup_tags(conn, [file])

        print_file_info(tagged_file[0])

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

    """Completer for `tag[child,child[grandchild]]`-style expressions."""

    def __init__(self, known_tags: set[str]):
        self.known_tags = known_tags

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        cut = max(text.rfind(d) for d in DELIMS)

        partial = text[cut + 1 :].lstrip()

        depth = text.count("[") - text.count("]")

        if depth > 0 and text[-1] != ",":
            yield Completion("]", start_position=0, display_meta="close group")

        # TODO: consider case-insensitive completions
        for tag in sorted(t for t in self.known_tags if t.startswith(partial)):
            yield Completion(tag, start_position=-len(partial))


class REPL(cmd.Cmd):
    prompt = "> "

    def __init__(self, session: ReviewSession):
        self.session = session
        self.pt: PromptSession = PromptSession()

        # completer for tags
        self.tag_completer = TagCompleter(session.known_tags)

        # completer for commands
        commands = [
            k.removeprefix("do_")
            for k in vars(REPL)
            if k.startswith("do_") and k != "do_EOF"
        ]
        self.cmd_completer = WordCompleter(sorted([*commands, "help"]))

        super().__init__()

    def _prompt(self):
        s = self.session
        return f"{(s.index + 1)} / {len(s.items)} {s.current.name} > "

    def run(self):
        while True:
            try:
                line = self.pt.prompt(self._prompt(), completer=self.cmd_completer)
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
        tag_expr = self.pt.prompt("Add tags: ", completer=self.tag_completer)

        try:
            self.session.add_tags(tag_expr)
            print(tag_expr)
        except (ValueError, UnexpectedToken, UnexpectedCharacters) as e:
            print(e)

    def do_info(self, arg):
        self.session.file_info()


@click.command()
@click.argument("file", type=click.File("r"))
@click.pass_obj
def review(vault: LazyVault, file: TextIO):
    lines = [Path(l.strip()) for l in file]

    # TODO: still bug when reading from stdin

    session = ReviewSession(vault, lines)

    repl = REPL(session)

    repl.run()
