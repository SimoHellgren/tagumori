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

    def test_info_by_inode(self, runner, vault, tagged_file):
        """Looking up by inode should return the file."""
        inode = tagged_file.stat().st_ino

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", "--inode", str(inode)]
        )

        assert result.exit_code == 0
        assert str(tagged_file) in result.output
        assert "rock" in result.output

    def test_info_by_inode_short_flag(self, runner, vault, tagged_file):
        """The -i short flag should work."""
        inode = tagged_file.stat().st_ino

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", "-i", str(inode)]
        )

        assert result.exit_code == 0
        assert str(tagged_file) in result.output

    def test_info_by_inode_not_found(self, runner, vault, tagged_file):
        """Looking up non-existent inode should return nothing."""
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", "--inode", "999999999"]
        )

        assert result.exit_code == 0
        assert result.output == ""

    def test_info_inode_and_path_mutually_exclusive(self, runner, vault, tagged_file):
        """Cannot use both --inode and file paths."""
        inode = tagged_file.stat().st_ino

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "info", "--inode", str(inode), str(tagged_file)],
        )

        assert result.exit_code != 0
        assert "Cannot use both" in result.output

    def test_info_requires_inode_or_path(self, runner, vault):
        """Must provide either --inode or file paths."""
        result = runner.invoke(cli, ["--vault", str(vault), "file", "info"])

        assert result.exit_code != 0
        assert "Provide file path or --inode" in result.output


class TestFileEdit:
    def test_edit_refresh_updates_inode(self, runner, vault, tagged_file, tmp_path):
        """--refresh should update inode/device from the file's current path."""
        # Create a mismatch: move original, create new file at same path
        backup = tmp_path / "backup.txt"
        tagged_file.rename(backup)
        tagged_file.write_text("new content")

        # Verify mismatch exists
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )
        assert "Mismatch" in info_result.output

        # Run refresh
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "edit", str(tagged_file), "--refresh"]
        )
        assert result.exit_code == 0

        # Verify inode now matches
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )
        assert "OK" in info_result.output

    def test_edit_refresh_multiple_files(self, runner, vault, sample_files, tmp_path):
        """--refresh should work with multiple files."""
        file1, file2 = sample_files

        # Add files to vault
        runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(file1), str(file2)]
        )

        # Create mismatches
        for f in sample_files:
            backup = tmp_path / f"backup_{f.name}"
            f.rename(backup)
            f.write_text("new content")

        # Refresh both
        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "edit", str(file1), str(file2), "--refresh"],
        )
        assert result.exit_code == 0

        # Both should now be OK
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(file1), str(file2)]
        )
        assert info_result.output.count("OK") == 2

    def test_edit_path_updates_record(self, runner, vault, tagged_file, tmp_path):
        """--path should point the record to a new file."""
        new_file = tmp_path / "newfile.txt"
        new_file.write_text("new content")

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "edit", str(tagged_file), "--path", str(new_file)],
        )
        assert result.exit_code == 0

        # Old path should no longer be in vault
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )
        assert str(tagged_file) not in info_result.output or info_result.exit_code != 0

        # New path should be in vault with the tags
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(new_file)]
        )
        assert str(new_file) in info_result.output
        assert "rock" in info_result.output

    def test_edit_relocate_finds_moved_file(self, runner, vault, tagged_file, tmp_path):
        """--relocate should find a file that was moved."""
        # Move the file to a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        new_location = subdir / tagged_file.name
        tagged_file.rename(new_location)

        # Record should now show "Not found"
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(tagged_file)]
        )
        assert "Not found" in info_result.output

        # Relocate searching from tmp_path
        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "edit", str(tagged_file), "--relocate", str(tmp_path)],
        )
        assert result.exit_code == 0

        # Record should now point to new location
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(new_location)]
        )
        assert str(new_location) in info_result.output
        assert "rock" in info_result.output

    def test_edit_no_files_fails(self, runner, vault):
        """Must provide at least one file."""
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "edit", "--refresh"]
        )

        assert result.exit_code != 0
        assert "No files provided" in result.output

    def test_edit_multiple_options_fails(self, runner, vault, tagged_file, tmp_path):
        """Cannot use multiple edit options together."""
        new_file = tmp_path / "newfile.txt"
        new_file.write_text("content")

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "edit", str(tagged_file), "--refresh", "--path", str(new_file)],
        )

        assert result.exit_code != 0
        assert "Can only provide one of" in result.output

    def test_edit_path_with_multiple_files_fails(self, runner, vault, sample_files, tmp_path):
        """Cannot use --path with multiple files."""
        file1, file2 = sample_files
        runner.invoke(
            cli, ["--vault", str(vault), "file", "add", str(file1), str(file2)]
        )

        new_file = tmp_path / "newfile.txt"
        new_file.write_text("content")

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "edit", str(file1), str(file2), "--path", str(new_file)],
        )

        assert result.exit_code != 0
        assert "Can't provide multiple files" in result.output


class TestFileCheck:
    def test_check_no_issues(self, runner, vault, tagged_file):
        """Healthy vault should report no issues."""
        result = runner.invoke(cli, ["--vault", str(vault), "file", "check"])

        assert result.exit_code == 0
        assert "No issues found" in result.output

    def test_check_finds_not_found(self, runner, vault, tagged_file):
        """Should report files whose path no longer exists."""
        tagged_file.unlink()

        result = runner.invoke(cli, ["--vault", str(vault), "file", "check"])

        assert result.exit_code == 0
        assert "NOT FOUND" in result.output
        assert str(tagged_file) in result.output

    def test_check_finds_mismatch(self, runner, vault, tagged_file, tmp_path):
        """Should report files with inode mismatch."""
        # Create mismatch: move original, create new file at same path
        backup = tmp_path / "backup.txt"
        tagged_file.rename(backup)
        tagged_file.write_text("new content")

        result = runner.invoke(cli, ["--vault", str(vault), "file", "check"])

        assert result.exit_code == 0
        assert "MISMATCH" in result.output
        assert str(tagged_file) in result.output

    def test_check_fix_does_not_fix_mismatch(self, runner, vault, tagged_file, tmp_path):
        """--fix should NOT auto-fix mismatches (user must decide)."""
        backup = tmp_path / "backup.txt"
        tagged_file.rename(backup)
        tagged_file.write_text("new content")

        result = runner.invoke(cli, ["--vault", str(vault), "file", "check", "--fix"])

        assert result.exit_code == 0
        assert "MISMATCH" in result.output
        assert "(fixed)" not in result.output

        # Still shows mismatch on subsequent check
        result = runner.invoke(cli, ["--vault", str(vault), "file", "check"])
        assert "MISMATCH" in result.output

    def test_check_finds_inode_missing(self, runner, vault, sample_file):
        """Should report files with missing inode."""
        import sqlite3

        # Add file to vault
        runner.invoke(cli, ["--vault", str(vault), "file", "add", str(sample_file)])

        # Manually clear the inode/device to simulate legacy data
        conn = sqlite3.connect(vault)
        conn.execute("UPDATE file SET inode = NULL, device = NULL")
        conn.commit()
        conn.close()

        result = runner.invoke(cli, ["--vault", str(vault), "file", "check"])

        assert result.exit_code == 0
        assert "INODE MISSING" in result.output
        assert str(sample_file) in result.output

    def test_check_fix_fixes_inode_missing(self, runner, vault, sample_file):
        """--fix should populate missing inodes."""
        import sqlite3

        # Add file to vault
        runner.invoke(cli, ["--vault", str(vault), "file", "add", str(sample_file)])

        # Manually clear the inode/device
        conn = sqlite3.connect(vault)
        conn.execute("UPDATE file SET inode = NULL, device = NULL")
        conn.commit()
        conn.close()

        result = runner.invoke(cli, ["--vault", str(vault), "file", "check", "--fix"])

        assert result.exit_code == 0
        assert "INODE MISSING" in result.output
        assert "(fixed)" in result.output

        # Subsequent check should be clean
        result = runner.invoke(cli, ["--vault", str(vault), "file", "check"])
        assert "No issues found" in result.output


class TestFileMv:
    def test_mv_single_file(self, runner, vault, tagged_file, tmp_path):
        """Move a single file to a new location."""
        dst = tmp_path / "moved.txt"

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "mv", str(tagged_file), "--to", str(dst)]
        )

        assert result.exit_code == 0
        assert "Moved" in result.output

        # Original file should be gone
        assert not tagged_file.exists()

        # New file should exist
        assert dst.exists()

        # Tags should be preserved
        info_result = runner.invoke(
            cli, ["--vault", str(vault), "file", "info", str(dst)]
        )
        assert "rock" in info_result.output

    def test_mv_to_directory(self, runner, vault, tagged_file, tmp_path):
        """Move file to a directory (keeps original name)."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "mv", str(tagged_file), "--to", str(subdir)]
        )

        assert result.exit_code == 0

        expected_dst = subdir / tagged_file.name
        assert expected_dst.exists()
        assert not tagged_file.exists()

    def test_mv_multiple_files_to_directory(self, runner, vault, sample_files, tmp_path):
        """Move multiple files to a directory."""
        file1, file2 = sample_files

        # Add files to vault
        runner.invoke(cli, ["--vault", str(vault), "file", "add", str(file1), str(file2)])

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "mv", str(file1), str(file2), "--to", str(subdir)],
        )

        assert result.exit_code == 0
        assert (subdir / file1.name).exists()
        assert (subdir / file2.name).exists()
        assert not file1.exists()
        assert not file2.exists()

    def test_mv_multiple_files_to_non_directory_fails(self, runner, vault, sample_files, tmp_path):
        """Cannot move multiple files to a non-directory destination."""
        file1, file2 = sample_files

        runner.invoke(cli, ["--vault", str(vault), "file", "add", str(file1), str(file2)])

        dst = tmp_path / "single_file.txt"

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "mv", str(file1), str(file2), "--to", str(dst)],
        )

        assert result.exit_code != 0
        assert "must be a directory" in result.output

    def test_mv_untracked_file_fails(self, runner, vault, sample_file, tmp_path):
        """Cannot move files not tracked in vault."""
        dst = tmp_path / "moved.txt"

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "mv", str(sample_file), "--to", str(dst)]
        )

        assert result.exit_code != 0
        assert "not tracked" in result.output

    def test_mv_no_sources_fails(self, runner, vault, tmp_path):
        """Must provide at least one source file."""
        dst = tmp_path / "somewhere"

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "mv", "--to", str(dst)]
        )

        assert result.exit_code != 0
        assert "No source files" in result.output

    def test_mv_requires_to_option(self, runner, vault, tagged_file):
        """--to is required."""
        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "mv", str(tagged_file)]
        )

        assert result.exit_code != 0
        assert "--to" in result.output

    def test_mv_overwrite_prompts_confirmation(self, runner, vault, tagged_file, tmp_path):
        """Moving to existing file prompts for confirmation."""
        existing = tmp_path / "existing.txt"
        existing.write_text("original content")

        # Answer "no" to confirmation
        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "mv", str(tagged_file), "--to", str(existing)],
            input="n\n",
        )

        assert result.exit_code != 0  # Aborted

        # Original files should be untouched
        assert tagged_file.exists()
        assert existing.read_text() == "original content"

    def test_mv_overwrite_with_confirmation(self, runner, vault, tagged_file, tmp_path):
        """Moving to existing file with 'yes' confirmation overwrites."""
        existing = tmp_path / "existing.txt"
        existing.write_text("original content")

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "mv", str(tagged_file), "--to", str(existing)],
            input="y\n",
        )

        assert result.exit_code == 0
        assert not tagged_file.exists()
        assert existing.read_text() == "test content"  # From tagged_file fixture

    def test_mv_force_skips_confirmation(self, runner, vault, tagged_file, tmp_path):
        """--force skips overwrite confirmation."""
        existing = tmp_path / "existing.txt"
        existing.write_text("original content")

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "mv", str(tagged_file), "--to", str(existing), "--force"],
        )

        assert result.exit_code == 0
        assert not tagged_file.exists()
        assert existing.read_text() == "test content"

    def test_mv_force_short_flag(self, runner, vault, tagged_file, tmp_path):
        """-f short flag works for --force."""
        existing = tmp_path / "existing.txt"
        existing.write_text("original content")

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "file", "mv", str(tagged_file), "--to", str(existing), "-f"],
        )

        assert result.exit_code == 0
        assert existing.read_text() == "test content"

    def test_mv_short_to_flag(self, runner, vault, tagged_file, tmp_path):
        """-t short flag works for --to."""
        dst = tmp_path / "moved.txt"

        result = runner.invoke(
            cli, ["--vault", str(vault), "file", "mv", str(tagged_file), "-t", str(dst)]
        )

        assert result.exit_code == 0
        assert dst.exists()
