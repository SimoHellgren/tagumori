import re
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from tagumori.cli import cli
from tagumori.db.init import init_db

VAULT_ID = re.compile(r"tagumori-[0-9a-f]{6}")


def pointer_of(directory: Path) -> Path:
    return directory / ".tagumori" / "pointer"


def vault_id_of(directory: Path) -> str:
    return pointer_of(directory).read_text().strip()


def db_dirs(data_home: Path) -> list[str]:
    """Names of the vault directories in the data dir (it may not exist yet)."""
    if not data_home.exists():
        return []

    return sorted(p.name for p in data_home.iterdir())


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """An empty directory to initialise a vault in."""
    path = tmp_path / "project"
    path.mkdir()
    return path


@pytest.fixture
def initialized(runner: CliRunner, project: Path) -> Path:
    """A directory where `tm db init` has already succeeded."""
    result = runner.invoke(cli, ["db", "init", str(project)])
    assert result.exit_code == 0, result.output
    return project


class TestInit:
    def test_writes_pointer_with_vault_id(self, runner, project):
        result = runner.invoke(cli, ["db", "init", str(project)])

        assert result.exit_code == 0
        assert VAULT_ID.fullmatch(vault_id_of(project))

    def test_creates_db_in_data_dir(self, runner, project, data_home):
        runner.invoke(cli, ["db", "init", str(project)])

        db_path = data_home / vault_id_of(project) / "vault.db"
        assert db_path.is_file()
        assert db_dirs(data_home) == [vault_id_of(project)]

        with sqlite3.connect(db_path) as conn:
            tables = {
                name
                for (name,) in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert {"file", "tag", "file_tag"} <= tables

    def test_creates_no_db_in_the_project(self, runner, project):
        runner.invoke(cli, ["db", "init", str(project)])

        assert sorted(p.name for p in project.iterdir()) == [".tagumori"]
        assert [p.name for p in (project / ".tagumori").iterdir()] == ["pointer"]

    @pytest.mark.parametrize("xdg", [None, ""], ids=["unset", "empty"])
    def test_falls_back_to_home_without_xdg_data_home(
        self, runner, project, tmp_path, monkeypatch, xdg
    ):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        if xdg is None:
            monkeypatch.delenv("XDG_DATA_HOME")
        else:
            monkeypatch.setenv("XDG_DATA_HOME", xdg)

        result = runner.invoke(cli, ["db", "init", str(project)])

        assert result.exit_code == 0
        db_path = home / ".local/share/tagumori" / vault_id_of(project) / "vault.db"
        assert db_path.is_file()

    def test_defaults_to_current_directory(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)

        result = runner.invoke(cli, ["db", "init"])

        assert result.exit_code == 0
        assert VAULT_ID.fullmatch(vault_id_of(project))

    def test_creates_missing_directory(self, runner, tmp_path, data_home):
        target = tmp_path / "does" / "not" / "exist"

        result = runner.invoke(cli, ["db", "init", str(target)])

        assert result.exit_code == 0
        assert (data_home / vault_id_of(target) / "vault.db").is_file()

    def test_each_vault_gets_its_own_id(self, runner, tmp_path, data_home):
        first, second = tmp_path / "first", tmp_path / "second"
        first.mkdir()
        second.mkdir()

        runner.invoke(cli, ["db", "init", str(first)])
        runner.invoke(cli, ["db", "init", str(second)])

        assert vault_id_of(first) != vault_id_of(second)
        assert len(db_dirs(data_home)) == 2

    def test_retries_on_id_collision(self, runner, tmp_path, data_home, monkeypatch):
        ids = iter(["aaaaaa", "aaaaaa", "bbbbbb"])
        monkeypatch.setattr("secrets.token_hex", lambda nbytes=None: next(ids))
        first, second = tmp_path / "first", tmp_path / "second"
        first.mkdir()
        second.mkdir()

        runner.invoke(cli, ["db", "init", str(first)])
        result = runner.invoke(cli, ["db", "init", str(second)])

        assert result.exit_code == 0
        assert vault_id_of(first) == "tagumori-aaaaaa"
        assert vault_id_of(second) == "tagumori-bbbbbb"
        assert db_dirs(data_home) == ["tagumori-aaaaaa", "tagumori-bbbbbb"]


class TestInitWhenAlreadyThere:
    """`init` must never create a second db where a vault is already set up."""

    def test_second_init_is_refused(self, runner, initialized, data_home):
        before = vault_id_of(initialized)

        result = runner.invoke(cli, ["db", "init", str(initialized)])

        assert result.exit_code != 0
        assert "already initialized" in result.output.lower()
        assert vault_id_of(initialized) == before
        assert db_dirs(data_home) == [before]

    def test_pointer_whose_db_is_missing_is_refused(
        self, runner, project, data_home
    ):
        pointer_of(project).parent.mkdir()
        pointer_of(project).write_text("tagumori-abcdef")

        result = runner.invoke(cli, ["db", "init", str(project)])

        assert result.exit_code != 0
        assert "tagumori-abcdef" in result.output
        assert vault_id_of(project) == "tagumori-abcdef"
        assert db_dirs(data_home) == []

    def test_empty_pointer_is_treated_as_uninitialized(self, runner, project):
        """What a crash between claiming the pointer and writing the id leaves."""
        pointer_of(project).parent.mkdir()
        pointer_of(project).touch()

        result = runner.invoke(cli, ["db", "init", str(project)])

        assert result.exit_code == 0
        assert VAULT_ID.fullmatch(vault_id_of(project))

    def test_pointer_with_path_traversal_is_rejected(
        self, runner, project, data_home
    ):
        pointer_of(project).parent.mkdir()
        pointer_of(project).write_text("../evil")

        result = runner.invoke(cli, ["db", "init", str(project)])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower()
        assert db_dirs(data_home) == []


class TestInitFailure:
    def test_failure_leaves_nothing_behind(
        self, runner, project, data_home, monkeypatch
    ):
        def explode(path: Path) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr("tagumori.commands.db.init_db", explode)

        result = runner.invoke(cli, ["db", "init", str(project)])

        assert result.exit_code != 0
        assert db_dirs(data_home) == []
        assert not pointer_of(project).exists()

    def test_can_init_again_after_a_failure(
        self, runner, project, data_home, monkeypatch
    ):
        with monkeypatch.context() as m:
            m.setattr(
                "tagumori.commands.db.init_db",
                lambda path: (_ for _ in ()).throw(RuntimeError("boom")),
            )
            runner.invoke(cli, ["db", "init", str(project)])

        result = runner.invoke(cli, ["db", "init", str(project)])

        assert result.exit_code == 0
        assert db_dirs(data_home) == [vault_id_of(project)]


class TestDiscovery:
    def test_finds_pointer_in_current_directory(
        self, runner, initialized, data_home, monkeypatch
    ):
        monkeypatch.chdir(initialized)

        result = runner.invoke(cli, ["db", "info"])

        assert result.exit_code == 0
        expected = data_home / vault_id_of(initialized) / "vault.db"
        assert str(expected) in result.output

    def test_finds_pointer_in_a_parent_directory(
        self, runner, initialized, data_home, monkeypatch
    ):
        nested = initialized / "a" / "b"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        result = runner.invoke(cli, ["db", "info"])

        assert result.exit_code == 0
        expected = data_home / vault_id_of(initialized) / "vault.db"
        assert str(expected) in result.output

    def test_no_vault_anywhere(self, runner, tmp_path, monkeypatch):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)

        result = runner.invoke(cli, ["ls"])

        assert result.exit_code != 0
        assert "Vault not found" in result.output

    def test_vault_option_overrides_discovery(
        self, runner, initialized, vault, monkeypatch
    ):
        monkeypatch.chdir(initialized)

        result = runner.invoke(cli, ["--vault", str(vault), "db", "info"])

        assert result.exit_code == 0
        assert str(vault) in result.output

    def test_empty_pointer_is_not_a_vault(self, runner, project, monkeypatch):
        pointer_of(project).parent.mkdir()
        pointer_of(project).touch()
        monkeypatch.chdir(project)

        result = runner.invoke(cli, ["ls"])

        assert result.exit_code != 0
        assert "Vault not found" in result.output

    def test_pointer_with_trailing_newline(
        self, runner, initialized, data_home, monkeypatch
    ):
        pointer_of(initialized).write_text(vault_id_of(initialized) + "\n")
        monkeypatch.chdir(initialized)

        result = runner.invoke(cli, ["db", "info"])

        assert result.exit_code == 0

    def test_pointer_with_path_traversal_is_rejected(
        self, runner, project, data_home, monkeypatch
    ):
        """A real db outside the data dir must not be reachable via `../`."""
        # `data_home/../outside` only resolves if data_home itself exists
        data_home.mkdir(parents=True)
        outside = data_home.parent / "outside"
        outside.mkdir()
        init_db(outside / "vault.db")
        pointer_of(project).parent.mkdir()
        pointer_of(project).write_text("../outside")
        monkeypatch.chdir(project)

        result = runner.invoke(cli, ["db", "info"])

        assert result.exit_code != 0


class TestBackup:
    def test_backup_creates_file(self, invoke, tmp_path):
        backup_path = tmp_path / "backup.db"

        result = invoke("db", "backup", str(backup_path))

        assert result.exit_code == 0
        assert backup_path.exists()
        assert "Backup created" in result.output

    def test_backup_default_filename(self, invoke, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = invoke("db", "backup")

            assert result.exit_code == 0
            # Should create file with timestamp pattern
            backup_files = list(Path(".").glob("test_vault-*.db"))
            assert len(backup_files) == 1

    def test_backup_with_directory(self, invoke, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        result = invoke("db", "backup", "-d", str(backup_dir))

        assert result.exit_code == 0
        backup_files = list(backup_dir.glob("test_vault-*.db"))
        assert len(backup_files) == 1

    def test_backup_is_valid_sqlite(self, invoke, tmp_path, tagged_file):
        import sqlite3

        backup_path = tmp_path / "backup.db"
        invoke("db", "backup", str(backup_path))

        # Verify backup is valid and contains data
        conn = sqlite3.connect(backup_path)
        count = conn.execute("SELECT COUNT(*) FROM file").fetchone()[0]
        conn.close()

        assert count == 1

    def test_backup_existing_prompts(self, invoke, tmp_path):
        backup_path = tmp_path / "backup.db"
        backup_path.write_text("existing")

        # Say no to overwrite
        result = invoke("db", "backup", str(backup_path), input="n\n")

        assert result.exit_code != 0  # Aborted

    def test_backup_existing_overwrite(self, invoke, tmp_path):
        backup_path = tmp_path / "backup.db"
        backup_path.write_text("existing")

        # Say yes to overwrite
        result = invoke("db", "backup", str(backup_path), input="y\n")

        assert result.exit_code == 0
        assert backup_path.stat().st_size > len("existing")  # Now it's a real db


class TestMigrate:
    def test_migrate_runs_successfully(self, invoke):
        result = invoke("db", "migrate")

        assert result.exit_code == 0
        assert "Schema updated" in result.output

    def test_migrate_is_idempotent(self, invoke):
        # Run migrate twice - should succeed both times
        result1 = invoke("db", "migrate")
        result2 = invoke("db", "migrate")

        assert result1.exit_code == 0
        assert result2.exit_code == 0

    def test_migrate_preserves_existing_data(self, invoke, vault, tagged_file):
        import sqlite3

        # Verify data exists before migration
        conn = sqlite3.connect(vault)
        count_before = conn.execute("SELECT COUNT(*) FROM file").fetchone()[0]
        conn.close()

        # Run migration
        result = invoke("db", "migrate")
        assert result.exit_code == 0

        # Verify data still exists after migration
        conn = sqlite3.connect(vault)
        count_after = conn.execute("SELECT COUNT(*) FROM file").fetchone()[0]
        conn.close()

        assert count_before == count_after == 1

    def test_migrate_creates_query_table(self, invoke, vault):
        import sqlite3

        invoke("db", "migrate")

        conn = sqlite3.connect(vault)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='query'"
        ).fetchall()
        conn.close()

        assert len(tables) == 1


class TestInfo:
    def test_info_shows_basic_fields(self, invoke):
        result = invoke("db", "info")

        assert result.exit_code == 0
        assert "SQLite version:" in result.output
        assert "Schema version:" in result.output
        assert "Path:" in result.output
        assert "Size:" in result.output
        assert "Modified:" in result.output
        assert "Tables:" in result.output

    def test_info_shows_table_counts(self, invoke, tagged_file):
        result = invoke("db", "info")

        assert result.exit_code == 0
        assert "file:" in result.output
        assert "tag:" in result.output
        assert "file_tag:" in result.output
