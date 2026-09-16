class TestSave:
    def test_save_creates_query(self, invoke):
        result = invoke("query", "save", "my-query", "-s", "rock")

        assert result.exit_code == 0

    def test_save_duplicate_fails(self, invoke):
        invoke("query", "save", "my-query", "-s", "rock")

        result = invoke("query", "save", "my-query", "-s", "jazz")

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_save_with_force_overwrites(self, invoke):
        invoke("query", "save", "my-query", "-s", "rock")

        result = invoke("query", "save", "my-query", "-s", "jazz", "--force")

        assert result.exit_code == 0

    def test_save_with_all_options(self, invoke):
        result = invoke(
            "query", "save", "complex-query", "-s", "rock", "-e", "jazz",
            "-p", r"\.mp3$", "-i", "-v",
        )

        assert result.exit_code == 0


class TestLs:
    def test_ls_empty(self, invoke):
        result = invoke("query", "ls")

        assert result.exit_code == 0

    def test_ls_shows_saved_queries(self, invoke):
        invoke("query", "save", "my-query", "-s", "rock")

        result = invoke("query", "ls")

        assert result.exit_code == 0
        assert "my-query" in result.output

    def test_ls_long_shows_parameters(self, invoke):
        invoke("query", "save", "my-query", "-s", "rock", "-e", "jazz")

        result = invoke("query", "ls", "-l")

        assert result.exit_code == 0
        assert "-s rock" in result.output
        assert "-e jazz" in result.output


class TestRun:
    def test_run_executes_query(self, invoke, tagged_file):
        invoke("query", "save", "rock-files", "-s", "rock")

        result = invoke("query", "run", "rock-files")

        assert result.exit_code == 0
        assert str(tagged_file) in result.output

    def test_run_with_pattern_filters_queries(self, invoke, tagged_file):
        invoke("query", "save", "rock-files", "-s", "rock")
        invoke("query", "save", "jazz-files", "-s", "jazz")

        result = invoke("query", "run", "rock.*")

        assert result.exit_code == 0
        assert "[rock-files]" in result.output
        assert "[jazz-files]" not in result.output

    def test_run_writes_to_file(self, invoke, tagged_file, tmp_path):
        invoke("query", "save", "rock-files", "-s", "rock")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = invoke("query", "run", "rock-files", "--write", str(output_dir))

        assert result.exit_code == 0
        assert (output_dir / "rock-files").exists()
        assert str(tagged_file) in (output_dir / "rock-files").read_text()

    def test_run_nonexistent_query_silent(self, invoke):
        result = invoke("query", "run", "nonexistent")

        assert result.exit_code == 0


class TestDrop:
    def test_drop_deletes_query(self, invoke):
        invoke("query", "save", "my-query", "-s", "rock")

        result = invoke("query", "drop", "my-query")

        assert result.exit_code == 0

        # Verify it's gone
        ls_result = invoke("query", "ls")
        assert "my-query" not in ls_result.output

    def test_drop_nonexistent_fails(self, invoke):
        result = invoke("query", "drop", "nonexistent")

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_drop_multiple_queries(self, invoke):
        invoke("query", "save", "query1", "-s", "rock")
        invoke("query", "save", "query2", "-s", "jazz")

        result = invoke("query", "drop", "query1", "query2")

        assert result.exit_code == 0

        ls_result = invoke("query", "ls")
        assert "query1" not in ls_result.output
        assert "query2" not in ls_result.output
