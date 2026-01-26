from filetags.cli import cli


class TestVaultRequired:
    def test_command_without_vault_fails(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["ls"])

            assert result.exit_code != 0
            assert "does not exist" in result.output


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


class TestRemove:
    def test_remove_tag(self, runner, vault, tagged_file):
        result = runner.invoke(
            cli,
            ["--vault", str(vault), "remove", "-f", str(tagged_file), "-t", "rock"],
        )

        assert result.exit_code == 0


class TestSet:
    def test_set_replaces_tags(self, runner, vault, tagged_file):
        result = runner.invoke(
            cli, ["--vault", str(vault), "set", "-f", str(tagged_file), "-t", "jazz"]
        )

        assert result.exit_code == 0

        # Verify
        show_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )
        assert "jazz" in show_result.output


class TestDrop:
    def test_drop_removes_all_tags(self, runner, vault, tagged_file):
        result = runner.invoke(
            cli, ["--vault", str(vault), "drop", "-f", str(tagged_file)]
        )

        assert result.exit_code == 0


class TestLs:
    def test_ls_empty(self, runner, vault):
        result = runner.invoke(cli, ["--vault", str(vault), "ls"])

        assert result.exit_code == 0
        assert result.output == ""

    def test_ls_shows_files(self, runner, vault, tagged_file):
        result = runner.invoke(cli, ["--vault", str(vault), "ls"])

        assert result.exit_code == 0
        assert tagged_file.name in result.output

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
        assert (
            "subdir/nested.txt" in result.output
            or "subdir\\nested.txt" in result.output
        )
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

    def test_ls_long_format(self, runner, vault, tagged_file):
        result = runner.invoke(cli, ["--vault", str(vault), "ls", "-l"])

        assert result.exit_code == 0
        assert tagged_file.name in result.output
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

    def test_ls_prefix(self, runner, vault, tmp_path):
        """--prefix should prepend a path to the output after applying --relative-to."""
        subdir = tmp_path / "mount" / "server"
        subdir.mkdir(parents=True)
        file = subdir / "file.txt"
        file.write_text("content")

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file), "-t", "docs"]
        )

        result = runner.invoke(
            cli,
            [
                "--vault",
                str(vault),
                "ls",
                "--relative-to",
                str(subdir),
                "--prefix",
                "/remote",
            ],
        )

        assert result.exit_code == 0
        assert "/remote/file.txt" in result.output
        # Should not contain the original mount path
        assert str(tmp_path) not in result.output
