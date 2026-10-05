import cmd
from collections.abc import Callable

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.input.defaults import create_input

from tagumori.commands.review import ReviewSession

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

    def __init__(self, session: ReviewSession, autoinfo: bool = False):
        self.session = session
        self.autoinfo = autoinfo

        shared_input = create_input(always_prefer_tty=True)

        # session & completer for tags
        self.tag_session: PromptSession = PromptSession(input=shared_input)
        self.tag_completer = TagCompleter(session.known_tags)

        # session & completer for commands
        self.cmd_session: PromptSession = PromptSession(input=shared_input)
        commands = [
            k.removeprefix("do_")
            for k in vars(REPL)
            if k.startswith("do_") and k != "do_EOF"
        ]
        self.cmd_completer = WordCompleter(sorted([*commands, "help"]))

        super().__init__()

    def _prompt(self):
        s = self.session
        return f"{(s.index + 1)}/{len(s.items)} {s.current.name} > "

    def run(self):
        last = self.session.current
        if self.autoinfo:
            self.session.file_info()
        while True:
            try:
                line = self.cmd_session.prompt(
                    self._prompt(), completer=self.cmd_completer
                )
            except (EOFError, KeyboardInterrupt):
                break
            if self.onecmd(line):
                break
            if self.autoinfo and self.session.current != last:
                self.session.file_info()
                last = self.session.current

    def do_goto(self, arg):
        """Go to position (indexed from 1)"""
        try:
            position = int(arg)
        except ValueError:
            click.echo(f"'{arg}' is not an integer")
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
        click.echo()
        return True

    def _handle_tag_operation(
        self, prompt: str, verb: str, operation: Callable[[str], None]
    ):
        try:
            tag_expr = self.tag_session.prompt(prompt, completer=self.tag_completer)

        except (EOFError, KeyboardInterrupt):
            click.echo("Canceled.")
            return

        try:
            operation(tag_expr)
            click.echo(f"{verb}: {tag_expr}")

        except ValueError:
            click.echo(f"Invalid expression: {tag_expr!r}")

    def do_add(self, arg):
        self._handle_tag_operation("Add tags: ", "Added", self.session.add_tags)

    def do_set(self, arg):
        self._handle_tag_operation("Set tags: ", "Set", self.session.set_tags)

    def do_remove(self, arg):
        self._handle_tag_operation("Remove tags: ", "Removed", self.session.remove_tags)

    def do_flag(self, arg):
        self.session.add_tags("__flag")
        click.echo(f"Flagged {self.session.current}")

    def do_unflag(self, arg):
        self.session.remove_tags("__flag")
        click.echo(f"Unflagged {self.session.current}")

    def do_info(self, arg):
        self.session.file_info()
