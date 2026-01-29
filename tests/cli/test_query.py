from filetags.cli import cli


class TestSave:
    def test_save_creates_query(self, runner, vault):
        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "my-query", "-s", "rock"]
        )

        assert result.exit_code == 0

    def test_save_duplicate_fails(self, runner, vault):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "my-query", "-s", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "my-query", "-s", "jazz"]
        )

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_save_with_force_overwrites(self, runner, vault):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "my-query", "-s", "rock"]
        )

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "query", "save", "my-query", "-s", "jazz", "--force"],
        )

        assert result.exit_code == 0

    def test_save_with_all_options(self, runner, vault):
        result = runner.invoke(
            cli,
            [
                "--vault", str(vault),
                "query", "save", "complex-query",
                "-s", "rock",
                "-e", "jazz",
                "-p", r"\.mp3$",
                "-i",
                "-v",
            ],
        )

        assert result.exit_code == 0


class TestLs:
    def test_ls_empty(self, runner, vault):
        result = runner.invoke(cli, ["--vault", str(vault), "query", "ls"])

        assert result.exit_code == 0

    def test_ls_shows_saved_queries(self, runner, vault):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "my-query", "-s", "rock"]
        )

        result = runner.invoke(cli, ["--vault", str(vault), "query", "ls"])

        assert result.exit_code == 0
        assert "my-query" in result.output

    def test_ls_long_shows_parameters(self, runner, vault):
        runner.invoke(
            cli,
            ["--vault", str(vault), "query", "save", "my-query", "-s", "rock", "-e", "jazz"],
        )

        result = runner.invoke(cli, ["--vault", str(vault), "query", "ls", "-l"])

        assert result.exit_code == 0
        assert "-s rock" in result.output
        assert "-e jazz" in result.output


class TestRun:
    def test_run_executes_query(self, runner, vault, tagged_file):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "rock-files", "-s", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "run", "rock-files"]
        )

        assert result.exit_code == 0
        assert str(tagged_file) in result.output

    def test_run_with_pattern_filters_queries(self, runner, vault, tagged_file):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "rock-files", "-s", "rock"]
        )
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "jazz-files", "-s", "jazz"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "run", "rock.*"]
        )

        assert result.exit_code == 0
        assert "[rock-files]" in result.output
        assert "[jazz-files]" not in result.output

    def test_run_writes_to_file(self, runner, vault, tagged_file, tmp_path):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "rock-files", "-s", "rock"]
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = runner.invoke(
            cli,
            ["--vault", str(vault), "query", "run", "rock-files", "--write", str(output_dir)],
        )

        assert result.exit_code == 0
        assert (output_dir / "rock-files").exists()
        assert str(tagged_file) in (output_dir / "rock-files").read_text()

    def test_run_nonexistent_query_silent(self, runner, vault):
        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "run", "nonexistent"]
        )

        assert result.exit_code == 0


class TestDrop:
    def test_drop_deletes_query(self, runner, vault):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "my-query", "-s", "rock"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "drop", "my-query"]
        )

        assert result.exit_code == 0

        # Verify it's gone
        ls_result = runner.invoke(cli, ["--vault", str(vault), "query", "ls"])
        assert "my-query" not in ls_result.output

    def test_drop_nonexistent_fails(self, runner, vault):
        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "drop", "nonexistent"]
        )

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_drop_multiple_queries(self, runner, vault):
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "query1", "-s", "rock"]
        )
        runner.invoke(
            cli, ["--vault", str(vault), "query", "save", "query2", "-s", "jazz"]
        )

        result = runner.invoke(
            cli, ["--vault", str(vault), "query", "drop", "query1", "query2"]
        )

        assert result.exit_code == 0

        ls_result = runner.invoke(cli, ["--vault", str(vault), "query", "ls"])
        assert "query1" not in ls_result.output
        assert "query2" not in ls_result.output
