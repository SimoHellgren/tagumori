# tests/test_cli.py
from pathlib import Path

import pytest
from click.testing import CliRunner

from filetags.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def vault(tmp_path):
    """Creates a temporary vault file and returns its path."""
    vault_path = tmp_path / "test_vault.db"
    runner = CliRunner()
    runner.invoke(cli, ["init", str(vault_path)])
    return vault_path


@pytest.fixture
def sample_file(tmp_path):
    """Creates a temporary file to tag."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("test content")
    return file_path


# ============================================================
# Init command
# ============================================================


class TestInit:
    def test_init_creates_vault(self, runner, tmp_path):
        vault_path = tmp_path / "new_vault.db"

        result = runner.invoke(cli, ["init", str(vault_path)])

        assert result.exit_code == 0
        assert vault_path.exists()
        assert "created" in result.output

    def test_init_existing_vault(self, runner, vault):
        result = runner.invoke(cli, ["init", str(vault)])

        assert result.exit_code == 0
        assert "already exists" in result.output

    def test_init_default_path(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert Path("vault.db").exists()


# ============================================================
# Vault requirement
# ============================================================


class TestVaultRequired:
    def test_command_without_vault_fails(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["ls"])

            assert result.exit_code != 0
            assert "does not exist" in result.output


# ============================================================
# Add command
# ============================================================


class TestAdd:
    def test_add_single_tag(self, runner, vault, sample_file):
        result = runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        assert result.exit_code == 0

    def test_add_multiple_tags(self, runner, vault, sample_file):
        result = runner.invoke(
            cli,
            [
                "--vault",
                str(vault),
                "add",
                "-f",
                str(sample_file),
                "-t",
                "rock",
                "-t",
                "jazz",
            ],
        )

        assert result.exit_code == 0

    def test_add_nested_tag(self, runner, vault, sample_file):
        result = runner.invoke(
            cli,
            ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "genre[rock]"],
        )

        assert result.exit_code == 0

    def test_add_requires_file(self, runner, vault):
        result = runner.invoke(cli, ["--vault", str(vault), "add", "-t", "rock"])

        assert result.exit_code != 0

    def test_add_requires_tag(self, runner, vault, sample_file):
        result = runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file)]
        )

        assert result.exit_code != 0

    def test_add_nonexistent_file_fails(self, runner, vault, tmp_path):
        fake_file = tmp_path / "nonexistent.txt"

        result = runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(fake_file), "-t", "rock"]
        )

        assert result.exit_code != 0


# ============================================================
# Remove command
# ============================================================


class TestRemove:
    def test_remove_tag(self, runner, vault, sample_file):
        # First add a tag
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "remove", "-f", str(sample_file), "-t", "rock"],
        )

        assert result.exit_code == 0


# ============================================================
# Show command
# ============================================================


class TestShow:
    def test_show_file_tags(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(cli, ["--vault", str(vault), "show", str(sample_file)])

        assert result.exit_code == 0
        assert "rock" in result.output


# ============================================================
# Set command
# ============================================================


class TestSet:
    def test_set_replaces_tags(self, runner, vault, sample_file):
        # Add initial tag
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        # Set to different tag
        result = runner.invoke(
            cli, ["--vault", str(vault), "set", "-f", str(sample_file), "-t", "jazz"]
        )

        assert result.exit_code == 0

        # Verify
        show_result = runner.invoke(
            cli, ["--vault", str(vault), "show", str(sample_file)]
        )
        assert "jazz" in show_result.output


# ============================================================
# Drop command
# ============================================================


class TestDrop:
    def test_drop_removes_all_tags(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "drop", "-f", str(sample_file)]
        )

        assert result.exit_code == 0


# ============================================================
# Ls command
# ============================================================


class TestLs:
    def test_ls_empty(self, runner, vault):
        result = runner.invoke(cli, ["--vault", str(vault), "ls"])

        assert result.exit_code == 0
        assert result.output == ""

    def test_ls_shows_files(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(cli, ["--vault", str(vault), "ls"])

        assert result.exit_code == 0
        assert "sample.txt" in result.output

    def test_ls_relative_to(self, runner, vault, tmp_path):
        """--relative-to should display paths relative to the given directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file = subdir / "nested.txt"
        file.write_text("content")

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file), "-t", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "ls", "--relative-to", str(tmp_path)]
        )

        assert result.exit_code == 0
        # Should show relative path, not absolute
        assert "subdir/nested.txt" in result.output or "subdir\\nested.txt" in result.output
        assert str(tmp_path) not in result.output

    def test_ls_relative_to_cwd(self, runner, vault, tmp_path):
        """--relative-to . should work relative to current directory."""
        file = tmp_path / "file.txt"
        file.write_text("content")

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file), "-t", "rock"]
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["--vault", str(vault), "ls", "--relative-to", "."]
            )

            assert result.exit_code == 0
            assert "file.txt" in result.output

    def test_ls_relative_to_file_outside_base(self, runner, vault, tmp_path):
        """Files outside the base path should show absolute path or error gracefully."""
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        file = other_dir / "outside.txt"
        file.write_text("content")

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file), "-t", "rock"]
        )

        # Try to show relative to a different directory
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        result = runner.invoke(
            cli, ["--vault", str(vault), "ls", "--relative-to", str(base_dir)]
        )

        # Should either show absolute path or handle gracefully (not crash)
        assert result.exit_code == 0
        assert "outside.txt" in result.output

    def test_ls_long_format(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(cli, ["--vault", str(vault), "ls", "-l"])

        assert result.exit_code == 0
        assert "sample.txt" in result.output
        assert "rock" in result.output

    def test_ls_select_filter(self, runner, vault, tmp_path):
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file1), "-t", "rock"]
        )
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file2), "-t", "jazz"]
        )

        result = runner.invoke(cli, ["--vault", str(vault), "ls", "-s", "rock"])

        assert result.exit_code == 0
        assert "rock.txt" in result.output
        assert "jazz.txt" not in result.output

    def test_ls_exclude_filter(self, runner, vault, tmp_path):
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file1), "-t", "rock"]
        )
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file2), "-t", "jazz"]
        )

        result = runner.invoke(cli, ["--vault", str(vault), "ls", "-e", "rock"])

        assert result.exit_code == 0
        assert "rock.txt" not in result.output
        assert "jazz.txt" in result.output

    def test_ls_pattern_filter(self, runner, vault, tmp_path):
        file1 = tmp_path / "song.mp3"
        file2 = tmp_path / "document.pdf"
        file1.write_text("")
        file2.write_text("")

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file1), "-t", "music"]
        )
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file2), "-t", "docs"]
        )

        result = runner.invoke(cli, ["--vault", str(vault), "ls", "-p", r"\.mp3$"])

        assert result.exit_code == 0
        assert "song.mp3" in result.output
        assert "document.pdf" not in result.output


# ============================================================
# Tag subcommands
# ============================================================


class TestTagCommands:
    def test_tag_create(self, runner, vault):
        result = runner.invoke(
            cli, ["--vault", str(vault), "tag", "create", "-n", "rock"]
        )

        assert result.exit_code == 0

    def test_tag_create_with_category(self, runner, vault):
        result = runner.invoke(
            cli,
            ["--vault", str(vault), "tag", "create", "-n", "rock", "-c", "genre"],
        )

        assert result.exit_code == 0

    def test_tag_ls(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "jazz"])

        result = runner.invoke(cli, ["--vault", str(vault), "tag", "ls"])

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "jazz" in result.output

    def test_tag_ls_long(self, runner, vault):
        runner.invoke(
            cli,
            ["--vault", str(vault), "tag", "create", "-n", "rock", "-c", "genre"],
        )

        result = runner.invoke(cli, ["--vault", str(vault), "tag", "ls", "-l"])

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "genre" in result.output

    def test_tag_ls_pattern(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "jazz"])

        result = runner.invoke(cli, ["--vault", str(vault), "tag", "ls", "-p", "^r"])

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "jazz" not in result.output

    def test_tag_edit(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])

        result = runner.invoke(
            cli, ["--vault", str(vault), "tag", "edit", "rock", "-c", "genre"]
        )

        assert result.exit_code == 0

    def test_tag_edit_no_option_fails(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])

        result = runner.invoke(cli, ["--vault", str(vault), "tag", "edit", "rock"])

        assert result.exit_code != 0
        assert "Provide at least one option" in result.output

    def test_tag_edit_name_multiple_tags_fails(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "jazz"])

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "tag", "edit", "rock", "jazz", "-n", "newname"],
        )

        assert result.exit_code != 0
        assert "--name can't be present when multiple tags" in result.output

    def test_tag_edit_set_and_clear_category_fails(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])

        result = runner.invoke(
            cli,
            [
                "--vault",
                str(vault),
                "tag",
                "edit",
                "rock",
                "-c",
                "genre",
                "--clear-category",
            ],
        )

        assert result.exit_code != 0
        assert "Can't both set and clear" in result.output

    def test_tag_edit_clear_category(self, runner, vault):
        runner.invoke(
            cli,
            ["--vault", str(vault), "tag", "create", "-n", "rock", "-c", "genre"],
        )

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "tag", "edit", "rock", "--clear-category"],
        )

        assert result.exit_code == 0

        # Verify category is cleared
        ls_result = runner.invoke(cli, ["--vault", str(vault), "tag", "ls", "-l"])
        assert "rock" in ls_result.output
        assert "genre" not in ls_result.output

    def test_tag_delete(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])

        result = runner.invoke(
            cli, ["--vault", str(vault), "tag", "delete", "rock"], input="y\n"
        )

        assert result.exit_code == 0

    def test_tag_delete_abort(self, runner, vault):
        runner.invoke(cli, ["--vault", str(vault), "tag", "create", "-n", "rock"])

        result = runner.invoke(
            cli, ["--vault", str(vault), "tag", "delete", "rock"], input="n\n"
        )

        assert result.exit_code != 0  # Aborted

    def test_tag_replace(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "tag", "replace", "rock", "-n", "jazz"]
        )

        assert result.exit_code == 0


# ============================================================
# Tagalong subcommands
# ============================================================


class TestTagalongCommands:
    def test_tagalong_add(self, runner, vault):
        result = runner.invoke(
            cli,
            ["--vault", str(vault), "tagalong", "add", "-t", "rock", "-ta", "guitar"],
        )

        assert result.exit_code == 0

    def test_tagalong_ls(self, runner, vault):
        runner.invoke(
            cli,
            ["--vault", str(vault), "tagalong", "add", "-t", "rock", "-ta", "guitar"],
        )

        result = runner.invoke(cli, ["--vault", str(vault), "tagalong", "ls"])

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "guitar" in result.output
        assert "->" in result.output

    def test_tagalong_remove(self, runner, vault):
        runner.invoke(
            cli,
            ["--vault", str(vault), "tagalong", "add", "-t", "rock", "-ta", "guitar"],
        )

        result = runner.invoke(
            cli,
            [
                "--vault",
                str(vault),
                "tagalong",
                "remove",
                "-t",
                "rock",
                "-ta",
                "guitar",
            ],
        )

        assert result.exit_code == 0

        # Verify it's gone
        ls_result = runner.invoke(cli, ["--vault", str(vault), "tagalong", "ls"])
        assert "rock" not in ls_result.output

    def test_tagalong_apply(self, runner, vault, sample_file):
        runner.invoke(
            cli,
            ["--vault", str(vault), "tagalong", "add", "-t", "rock", "-ta", "guitar"],
        )
        runner.invoke(
            cli,
            [
                "--vault",
                str(vault),
                "add",
                "-f",
                str(sample_file),
                "-t",
                "rock",
                "--no-tagalongs",
            ],
        )

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "tagalong", "apply", "-f", str(sample_file)],
        )

        assert result.exit_code == 0

        # Verify tagalong was applied
        show_result = runner.invoke(
            cli, ["--vault", str(vault), "show", str(sample_file)]
        )
        assert "guitar" in show_result.output
