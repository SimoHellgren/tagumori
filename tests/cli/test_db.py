from pathlib import Path

from filetags.cli import cli


class TestInit:
    def test_init_creates_vault(self, runner, tmp_path):
        vault_path = tmp_path / "new_vault.db"

        result = runner.invoke(cli, ["db", "init", str(vault_path)])

        assert result.exit_code == 0
        assert vault_path.exists()
        assert "created" in result.output

    def test_init_existing_vault(self, runner, vault):
        result = runner.invoke(cli, ["db", "init", str(vault)])

        assert result.exit_code == 0
        assert "already exists" in result.output

    def test_init_default_path(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["db", "init"])

            assert result.exit_code == 0
            assert Path("vault.db").exists()


class TestBackup:
    def test_backup_creates_file(self, runner, vault, tmp_path):
        backup_path = tmp_path / "backup.db"

        result = runner.invoke(
            cli, ["--vault", str(vault), "db", "backup", str(backup_path)]
        )

        assert result.exit_code == 0
        assert backup_path.exists()
        assert "Backup created" in result.output

    def test_backup_default_filename(self, runner, vault, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["--vault", str(vault), "db", "backup"])

            assert result.exit_code == 0
            # Should create file with timestamp pattern
            backup_files = list(Path(".").glob("test_vault-*.db"))
            assert len(backup_files) == 1

    def test_backup_with_directory(self, runner, vault, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        result = runner.invoke(
            cli, ["--vault", str(vault), "db", "backup", "-d", str(backup_dir)]
        )

        assert result.exit_code == 0
        backup_files = list(backup_dir.glob("test_vault-*.db"))
        assert len(backup_files) == 1

    def test_backup_is_valid_sqlite(self, runner, vault, tmp_path, tagged_file):
        import sqlite3

        backup_path = tmp_path / "backup.db"
        runner.invoke(cli, ["--vault", str(vault), "db", "backup", str(backup_path)])

        # Verify backup is valid and contains data
        conn = sqlite3.connect(backup_path)
        count = conn.execute("SELECT COUNT(*) FROM file").fetchone()[0]
        conn.close()

        assert count == 1

    def test_backup_existing_prompts(self, runner, vault, tmp_path):
        backup_path = tmp_path / "backup.db"
        backup_path.write_text("existing")

        # Say no to overwrite
        result = runner.invoke(
            cli, ["--vault", str(vault), "db", "backup", str(backup_path)], input="n\n"
        )

        assert result.exit_code != 0  # Aborted

    def test_backup_existing_overwrite(self, runner, vault, tmp_path):
        backup_path = tmp_path / "backup.db"
        backup_path.write_text("existing")

        # Say yes to overwrite
        result = runner.invoke(
            cli, ["--vault", str(vault), "db", "backup", str(backup_path)], input="y\n"
        )

        assert result.exit_code == 0
        assert backup_path.stat().st_size > len("existing")  # Now it's a real db


class TestMigrate:
    def test_migrate_runs_successfully(self, runner, vault):
        result = runner.invoke(cli, ["--vault", str(vault), "db", "migrate"])

        assert result.exit_code == 0
        assert "Schema updated" in result.output

    def test_migrate_is_idempotent(self, runner, vault):
        # Run migrate twice - should succeed both times
        result1 = runner.invoke(cli, ["--vault", str(vault), "db", "migrate"])
        result2 = runner.invoke(cli, ["--vault", str(vault), "db", "migrate"])

        assert result1.exit_code == 0
        assert result2.exit_code == 0

    def test_migrate_preserves_existing_data(self, runner, vault, tagged_file):
        import sqlite3

        # Verify data exists before migration
        conn = sqlite3.connect(vault)
        count_before = conn.execute("SELECT COUNT(*) FROM file").fetchone()[0]
        conn.close()

        # Run migration
        result = runner.invoke(cli, ["--vault", str(vault), "db", "migrate"])
        assert result.exit_code == 0

        # Verify data still exists after migration
        conn = sqlite3.connect(vault)
        count_after = conn.execute("SELECT COUNT(*) FROM file").fetchone()[0]
        conn.close()

        assert count_before == count_after == 1

    def test_migrate_creates_query_table(self, runner, vault):
        import sqlite3

        runner.invoke(cli, ["--vault", str(vault), "db", "migrate"])

        conn = sqlite3.connect(vault)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='query'"
        ).fetchall()
        conn.close()

        assert len(tables) == 1


class TestInfo:
    def test_info_shows_basic_fields(self, runner, vault):
        result = runner.invoke(cli, ["--vault", str(vault), "db", "info"])

        assert result.exit_code == 0
        assert "SQLite version:" in result.output
        assert "Schema version:" in result.output
        assert "Path:" in result.output
        assert "Size:" in result.output
        assert "Modified:" in result.output
        assert "Tables:" in result.output

    def test_info_shows_table_counts(self, runner, vault, tagged_file):
        result = runner.invoke(cli, ["--vault", str(vault), "db", "info"])

        assert result.exit_code == 0
        assert "file:" in result.output
        assert "tag:" in result.output
        assert "file_tag:" in result.output
