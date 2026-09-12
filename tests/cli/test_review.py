from pathlib import Path

import click
import pytest
from prompt_toolkit.document import Document

from tagumori import crud, service
from tagumori.cli import cli
from tagumori.commands import review as review_module
from tagumori.commands.context import LazyVault
from tagumori.commands.review import REPL, ReviewSession, TagCompleter
from tagumori.query.parser import UnexpectedToken


@pytest.fixture
def lazy_vault(vault) -> LazyVault:
    """A LazyVault over the temporary vault file."""
    return LazyVault(vault, click.Context(click.Command("test")))


@pytest.fixture
def session(lazy_vault, sample_files) -> ReviewSession:
    """A session over two untagged files."""
    return ReviewSession(lazy_vault, list(sample_files))


class ScriptedPrompts:
    """Canned answers for prompt(), plus a record of the prompts shown."""

    def __init__(self):
        self.answers: list[str] = []
        self.seen: list[str] = []

    def script(self, *answers: str) -> None:
        self.answers.extend(answers)


@pytest.fixture
def prompts(monkeypatch) -> ScriptedPrompts:
    """Replaces PromptSession with a scripted stub, so no terminal is needed.

    Answers are consumed in order by every prompt() call - command prompts and
    tag prompts alike. When the script runs out, EOFError is raised, which ends
    REPL.run() the same way Ctrl-D would.
    """
    scripted = ScriptedPrompts()

    class StubPromptSession:
        def __init__(self, *args, **kwargs):
            pass

        def prompt(self, text="", *args, **kwargs):
            scripted.seen.append(text)
            if not scripted.answers:
                raise EOFError
            return scripted.answers.pop(0)

    monkeypatch.setattr(review_module, "PromptSession", StubPromptSession)
    return scripted


class TestNavigation:
    def test_current_starts_at_first_item(self, session, sample_files):
        assert session.current == sample_files[0]

    def test_next_advances(self, session, sample_files):
        session.next()

        assert session.current == sample_files[1]

    def test_next_clamps_at_last_item(self, session, sample_files):
        for _ in range(10):
            session.next()

        assert session.current == sample_files[-1]

    def test_prev_goes_back(self, session, sample_files):
        session.next()
        session.prev()

        assert session.current == sample_files[0]

    def test_prev_clamps_at_first_item(self, session, sample_files):
        session.prev()

        assert session.current == sample_files[0]

    def test_goto_moves_to_index(self, session, sample_files):
        session.goto(1)

        assert session.current == sample_files[1]

    def test_goto_past_end_leaves_index_unchanged(self, session, capsys):
        session.goto(99)

        assert session.index == 0
        assert "not in range" in capsys.readouterr().out

    def test_goto_negative_leaves_index_unchanged(self, session, capsys):
        session.goto(-1)

        assert session.index == 0
        assert "not in range" in capsys.readouterr().out


class TestKnownTags:
    def test_seeds_from_vault(self, lazy_vault, tagged_file):
        session = ReviewSession(lazy_vault, [tagged_file])

        assert session.known_tags == {"rock"}

    def test_empty_vault_seeds_nothing(self, session):
        assert session.known_tags == set()

    def test_add_tags_extends_known_tags(self, session):
        session.add_tags("jazz")

        assert "jazz" in session.known_tags

    def test_nested_expression_contributes_every_name(self, session):
        """Both the parent and the child should become completable."""
        session.add_tags("artist[Led Zeppelin]")

        assert {"artist", "Led Zeppelin"} <= session.known_tags

    def test_failed_add_does_not_extend_known_tags(self, session):
        with pytest.raises(ValueError):
            session.add_tags("a|b")

        assert session.known_tags == set()


class TestAddTags:
    def test_tags_are_persisted(self, session, lazy_vault, sample_files):
        session.add_tags("rock")

        with lazy_vault as conn:
            file = crud.file.get_by_path(conn, sample_files[0])
            assert file is not None
            tagged = service.lookup_tags(conn, [file])

        assert "rock" in str(tagged[0].tags)

    def test_applies_only_to_the_current_file(self, session, lazy_vault, sample_files):
        session.add_tags("rock")

        with lazy_vault as conn:
            other = crud.file.get_by_path(conn, sample_files[1])

        assert other is None

    def test_follows_the_cursor(self, session, lazy_vault, sample_files):
        session.next()
        session.add_tags("jazz")

        with lazy_vault as conn:
            file = crud.file.get_by_path(conn, sample_files[1])
            assert file is not None
            tagged = service.lookup_tags(conn, [file])

        assert "jazz" in str(tagged[0].tags)

    def test_nested_expression_is_stored_as_a_tree(self, session, lazy_vault, sample_files):
        session.add_tags("artist[Led Zeppelin]")

        with lazy_vault as conn:
            file = crud.file.get_by_path(conn, sample_files[0])
            assert file is not None
            tagged = service.lookup_tags(conn, [file])

        assert str(tagged[0].tags) == "artist[Led Zeppelin]"

    def test_each_add_commits_independently(self, lazy_vault, sample_files):
        """A later session must see what an earlier one wrote."""
        first = ReviewSession(lazy_vault, list(sample_files))
        first.add_tags("rock")

        second = ReviewSession(lazy_vault, list(sample_files))

        assert "rock" in second.known_tags

    def test_malformed_expression_raises(self, session):
        with pytest.raises(UnexpectedToken):
            session.add_tags("rock[")

    def test_non_storage_expression_is_rejected(self, session):
        """Operators are queries, not storable tags."""
        with pytest.raises(ValueError):
            session.add_tags("a|b")

    def test_invalid_expression_writes_nothing(self, session, lazy_vault, sample_files):
        """Validation happens before the file record is created."""
        with pytest.raises(ValueError):
            session.add_tags("!rock")

        with lazy_vault as conn:
            assert crud.file.get_by_path(conn, sample_files[0]) is None


class TestFileInfo:
    def test_untracked_file_reports_and_returns(self, session, capsys):
        session.file_info()

        assert "not in vault" in capsys.readouterr().out

    def test_tracked_file_shows_its_tags(self, lazy_vault, tagged_file, capsys):
        session = ReviewSession(lazy_vault, [tagged_file])

        session.file_info()

        assert "rock" in capsys.readouterr().out


def completions(completer: TagCompleter, text: str) -> list[str]:
    return [c.text for c in completer.get_completions(Document(text), None)]


class TestTagCompleter:
    @pytest.fixture
    def completer(self) -> TagCompleter:
        return TagCompleter({"rock", "rockabilly", "jazz", "Led Zeppelin"})

    def test_empty_input_offers_everything(self, completer):
        assert completions(completer, "") == [
            "Led Zeppelin",
            "jazz",
            "rock",
            "rockabilly",
        ]

    def test_completes_a_prefix(self, completer):
        assert completions(completer, "roc") == ["rock", "rockabilly"]

    def test_completes_a_name_containing_spaces(self, completer):
        """The token starts at the last delimiter, not at the last word."""
        assert completions(completer, "Led Z") == ["Led Zeppelin"]

    def test_completes_after_an_opening_bracket(self, completer):
        assert "rock" in completions(completer, "genre[roc")

    def test_completes_after_a_comma(self, completer):
        assert "rock" in completions(completer, "jazz,roc")

    def test_offers_closing_bracket_while_nested(self, completer):
        assert "]" in completions(completer, "genre[rock")

    def test_no_closing_bracket_at_top_level(self, completer):
        assert "]" not in completions(completer, "rock")

    def test_no_closing_bracket_directly_after_a_comma(self, completer):
        assert "]" not in completions(completer, "genre[rock,")

    def test_no_closing_bracket_once_balanced(self, completer):
        assert "]" not in completions(completer, "genre[rock]")

    def test_completion_replaces_the_partial_word(self, completer):
        (completion,) = completer.get_completions(Document("Led Z"), None)

        assert completion.start_position == -len("Led Z")

    def test_sees_tags_added_during_the_session(self, session):
        """The completer holds the session's live set, not a snapshot."""
        completer = TagCompleter(session.known_tags)
        session.add_tags("shoegaze")

        assert completions(completer, "shoe") == ["shoegaze"]


class TestREPL:
    def test_prompt_shows_position_and_filename(self, session, prompts, sample_files):
        repl = REPL(session)

        assert repl._prompt() == f"1 / 2 {sample_files[0].name} > "

    def test_prompt_tracks_the_cursor(self, session, prompts, sample_files):
        repl = REPL(session)
        session.next()

        assert repl._prompt() == f"2 / 2 {sample_files[1].name} > "

    def test_empty_line_advances(self, session, prompts):
        repl = REPL(session)

        repl.onecmd("")

        assert session.index == 1

    def test_next_and_prev_dispatch(self, session, prompts):
        repl = REPL(session)

        repl.onecmd("next")
        assert session.index == 1

        repl.onecmd("prev")
        assert session.index == 0

    def test_goto_is_one_indexed(self, session, prompts):
        repl = REPL(session)

        repl.onecmd("goto 2")

        assert session.index == 1

    def test_goto_rejects_non_integers(self, session, prompts, capsys):
        repl = REPL(session)

        repl.onecmd("goto banana")

        assert session.index == 0
        assert "not an integer" in capsys.readouterr().out

    def test_exit_stops_the_loop(self, session, prompts):
        repl = REPL(session)

        assert repl.onecmd("exit") is True

    def test_command_completer_lists_commands_but_not_eof(self, session, prompts):
        repl = REPL(session)

        words = repl.cmd_completer.words
        assert not callable(words)

        assert {"add", "exit", "goto", "info", "next", "prev", "help"} <= set(words)
        assert "EOF" not in words

    def test_add_stores_the_tags_entered_at_the_prompt(self, session, prompts):
        repl = REPL(session)
        prompts.script("rock")

        repl.onecmd("add")

        assert "rock" in session.known_tags

    def test_add_reports_a_parse_error_without_raising(self, session, prompts, capsys):
        repl = REPL(session)
        prompts.script("rock[")

        repl.onecmd("add")

        assert session.known_tags == set()
        assert "Unexpected token" in capsys.readouterr().out

    def test_run_exits_on_end_of_input(self, session, prompts):
        """An exhausted script raises EOFError, as Ctrl-D would."""
        repl = REPL(session)

        repl.run()

        assert session.index == 0

    def test_run_dispatches_a_scripted_session(self, session, prompts, sample_files):
        repl = REPL(session)
        prompts.script("next", "add", "rock", "exit")

        repl.run()

        assert session.index == 1
        assert "rock" in session.known_tags


class TestReviewCommand:
    def test_empty_input_file_is_reported(self, runner, vault, tmp_path):
        listing = tmp_path / "empty.txt"
        listing.write_text("")

        result = runner.invoke(
            cli, ["--vault", str(vault), "review", str(listing)]
        )

        assert result.exit_code == 0
        assert "empty" in result.output

    def test_blank_lines_only_is_treated_as_empty(self, runner, vault, tmp_path):
        listing = tmp_path / "blank.txt"
        listing.write_text("\n   \n\n")

        result = runner.invoke(
            cli, ["--vault", str(vault), "review", str(listing)]
        )

        assert result.exit_code == 0
        assert "empty" in result.output

    def test_missing_input_file_fails(self, runner, vault, tmp_path):
        result = runner.invoke(
            cli, ["--vault", str(vault), "review", str(tmp_path / "nope.txt")]
        )

        assert result.exit_code != 0

    def test_blank_lines_are_skipped(self, runner, vault, sample_files, prompts):
        """A trailing newline must not become Path('.') and pad the list."""
        listing = sample_files[0].parent / "list.txt"
        listing.write_text("\n".join(str(f) for f in sample_files) + "\n\n")

        result = runner.invoke(cli, ["--vault", str(vault), "review", str(listing)])

        assert result.exit_code == 0
        assert prompts.seen[0].startswith(f"1 / {len(sample_files)} ")

    def test_runs_a_scripted_session(self, runner, vault, sample_files, prompts):
        listing = sample_files[0].parent / "list.txt"
        listing.write_text("\n".join(str(f) for f in sample_files))
        prompts.script("add", "rock", "exit")

        result = runner.invoke(
            cli, ["--vault", str(vault), "review", str(listing)]
        )

        assert result.exit_code == 0

        conn = LazyVault(vault, click.Context(click.Command("test")))
        with conn as c:
            file = crud.file.get_by_path(c, sample_files[0])
            assert file is not None
            tagged = service.lookup_tags(c, [file])

        assert "rock" in str(tagged[0].tags)
