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

    def test_add_multiple_files(self, runner, vault, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(file1), str(file2)]
        )

        assert result.exit_code == 0

        # Verify both files are in db
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(file1), str(file2)]
        )
        assert "file1.txt" in info_result.output
        assert "file2.txt" in info_result.output

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

    def test_drop_multiple_files(self, runner, vault, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

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

    def test_drop_file_with_tags(self, runner, vault, sample_file):
        """Dropping a file should also remove its tags."""
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "drop", str(sample_file)], input="y\n"
        )

        assert result.exit_code == 0


class TestFileInfo:
    def test_info_shows_file_details(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )

        assert result.exit_code == 0
        assert str(sample_file) in result.output
        assert "rock" in result.output

    def test_info_existing_file_shows_exists(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )

        assert result.exit_code == 0
        assert "Exists" in result.output

    def test_info_missing_file_shows_not_found(self, runner, vault, sample_file):
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )
        # Delete the file after adding it to the vault
        sample_file.unlink()

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )

        assert result.exit_code == 0
        assert "Not found" in result.output

    def test_info_inode_ok(self, runner, vault, sample_file):
        """Inode should show OK when file's inode matches the record."""
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_info_inode_mismatch(self, runner, vault, sample_file, tmp_path):
        """Inode should show Mismatch when file's inode differs from record."""
        runner.invoke(
            cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
        )
        # Move original file away (keeps its inode), create new file at same path
        backup = tmp_path / "backup.txt"
        sample_file.rename(backup)
        sample_file.write_text("new content")

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )

        assert result.exit_code == 0
        assert "Mismatch" in result.output

    def test_info_multiple_files(self, runner, vault, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

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
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
        assert "rock" in result.output
        assert "jazz" in result.output
