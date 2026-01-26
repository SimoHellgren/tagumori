from filetags.cli import cli


class TestFileAdd:
    def test_add_single_file(self, runner, vault, sample_file):
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(sample_file)]
        )

        assert result.exit_code == 0

        # Verify file is in db (via file info)
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )
        assert str(sample_file) in info_result.output

    def test_add_multiple_files(self, runner, vault, sample_files):
        file1, file2 = sample_files

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(file1), str(file2)]
        )

        assert result.exit_code == 0

        # Verify both files are in db
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(file1), str(file2)]
        )
        assert file1.name in info_result.output
        assert file2.name in info_result.output

    def test_add_nonexistent_file_fails(self, runner, vault, tmp_path):
        fake_file = tmp_path / "nonexistent.txt"

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(fake_file)]
        )

        assert result.exit_code != 0

    def test_add_file_without_tags(self, runner, vault, sample_file):
        """File added via file add should have no tags."""
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(sample_file)]
        )

        assert result.exit_code == 0

        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )

        assert "Tags:" in info_result.output
        # Tags line should be empty (just "Tags: ")
        for line in info_result.output.split("\n"):
            if "Tags:" in line:
                # After "Tags: " there should be nothing (or empty)
                assert line.replace(" ", "") == "│Tags:│"


class TestFileDrop:
    def test_drop_removes_file_from_db(self, runner, vault, sample_file):
        runner.invoke(cli, ["--vault", str(vault), "file", "add", str(sample_file)])

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "drop", str(sample_file)], input="y\n"
        )

        assert result.exit_code == 0

        # Verify file is no longer in db
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )
        # file info on non-existent db record should return empty or error
        assert str(sample_file) not in info_result.output or info_result.exit_code != 0

    def test_drop_abort(self, runner, vault, sample_file):
        runner.invoke(cli, ["--vault", str(vault), "file", "add", str(sample_file)])

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "drop", str(sample_file)], input="n\n"
        )

        assert result.exit_code != 0  # Aborted

        # Verify file is still in db
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )
        assert str(sample_file) in info_result.output

    def test_drop_multiple_files(self, runner, vault, sample_files):
        file1, file2 = sample_files

        runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(file1), str(file2)]
        )

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "drop", str(file1), str(file2)],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "2 file(s)" in result.output

    def test_drop_file_with_tags(self, runner, vault, tagged_file):
        """Dropping a file should also remove its tags."""
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "drop", str(tagged_file)], input="y\n"
        )

        assert result.exit_code == 0


class TestFileInfo:
    def test_info_shows_file_details(self, runner, vault, tagged_file):
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )

        assert result.exit_code == 0
        assert str(tagged_file) in result.output
        assert "rock" in result.output

    def test_info_existing_file_shows_exists(self, runner, vault, tagged_file):
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )

        assert result.exit_code == 0
        assert "Exists" in result.output

    def test_info_missing_file_shows_not_found(self, runner, vault, tagged_file):
        # Delete the file after it was added to the vault
        tagged_file.unlink()

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )

        assert result.exit_code == 0
        assert "Not found" in result.output

    def test_info_inode_ok(self, runner, vault, tagged_file):
        """Inode should show OK when file's inode matches the record."""
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_info_inode_mismatch(self, runner, vault, tagged_file, tmp_path):
        """Inode should show Mismatch when file's inode differs from record."""
        # Move original file away (keeps its inode), create new file at same path
        backup = tmp_path / "backup.txt"
        tagged_file.rename(backup)
        tagged_file.write_text("new content")

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )

        assert result.exit_code == 0
        assert "Mismatch" in result.output

    def test_info_multiple_files(self, runner, vault, sample_files):
        file1, file2 = sample_files

        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file1), "-t", "rock"]
        )
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(file2), "-t", "jazz"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(file1), str(file2)]
        )

        assert result.exit_code == 0
        assert file1.name in result.output
        assert file2.name in result.output
        assert "rock" in result.output
        assert "jazz" in result.output
