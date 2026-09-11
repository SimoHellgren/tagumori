import cmd
import re
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from tagumori import crud
from tagumori.commands.context import LazyVault


@click.command()
@click.argument("file", type=click.File("r"))
@click.pass_obj
def review(vault: LazyVault, file):
    lines = [Path(l.strip()) for l in file]

    sys.stdin = open("/dev/tty")

    with vault as conn:
        data = crud.tag.get_all(conn)
        tags = {x.name for x in data}
        print(tags)

    completer = TagCompleter(lambda: sorted(tags))

    repl = REPL(lines, completer)

    repl.cmdloop()


TAG_CHARS = re.compile(r"[A-Za-z0-9_-]*$")


class TagCompleter(Completer):
    """Completer for `tag[child,child[grandchild]]`-style expressions."""

    def __init__(self, get_tags: Callable[[], Iterable[str]]):
        self.get_tags = get_tags

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        partial = TAG_CHARS.search(text).group(0)

        token_start = len(text) - len(partial)
        char_before_token = text[token_start - 1] if token_start > 0 else ""

        depth = text.count("[") - text.count("]")
        last_char = text[-1] if text else ""

        if depth > 0 and last_char != ",":
            yield Completion("]", start_position=0, display_meta="close group")

        if char_before_token in ("[", ",", ""):
            for tag in sorted(self.get_tags()):
                if tag.startswith(partial):
                    yield Completion(tag, start_position=-len(partial))


class REPL(cmd.Cmd):
    prompt = "> "

    def __init__(self, items: list[Path], completer: Completer):
        self.index = 0
        self.items = items

        self.promptsession: PromptSession = PromptSession()
        self.completer = completer

        super().__init__()

    @property
    def current_item(self) -> Path:
        return self.items[self.index]

    def refresh(self):
        """Print current item and position"""
        print(f"({self.index + 1}/{len(self.items)}) {self.current_item}")

    def preloop(self):
        self.refresh()
        return super().preloop()

    def postcmd(self, stop, line):
        if stop:
            return stop

        self.refresh()
        return stop

    def do_goto(self, arg):
        """Go to position (indexed from 1)"""
        try:
            position = int(arg)
        except ValueError:
            print(f"'{arg}' is not an integer")
            return

        if not 1 <= position <= len(self.items):
            print(f"{position} not in range [1,{len(self.items)}]")
            return

        self.index = position - 1

    def do_prev(self, arg):
        """Go back"""
        self.index = max(0, self.index - 1)

    def do_next(self, arg):
        """Move along"""
        self.index = min(len(self.items) - 1, self.index + 1)

    def do_exit(self, arg):
        """Exit the REPL"""
        return True

    def do_EOF(self, arg):
        """Exit the REPL"""
        print()
        return True

    def do_add(self, arg):
        result = self.promptsession.prompt("Add tags: ", completer=self.completer)

        new_tags = {x.replace("]", "").strip() for x in re.split(r"[\[,]", result)}

        print(result, new_tags)
