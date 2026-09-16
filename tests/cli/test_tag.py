class TestTagCommands:
    def test_tag_create(self, invoke):
        result = invoke("tag", "create", "-n", "rock")

        assert result.exit_code == 0

    def test_tag_create_with_category(self, invoke):
        result = invoke("tag", "create", "-n", "rock", "-c", "genre")

        assert result.exit_code == 0

    def test_tag_ls(self, invoke):
        invoke("tag", "create", "-n", "rock")
        invoke("tag", "create", "-n", "jazz")

        result = invoke("tag", "ls")

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "jazz" in result.output

    def test_tag_ls_long(self, invoke):
        invoke("tag", "create", "-n", "rock", "-c", "genre")

        result = invoke("tag", "ls", "-l")

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "genre" in result.output

    def test_tag_ls_pattern(self, invoke):
        invoke("tag", "create", "-n", "rock")
        invoke("tag", "create", "-n", "jazz")

        result = invoke("tag", "ls", "-p", "^r")

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "jazz" not in result.output

    def test_tag_edit(self, invoke):
        invoke("tag", "create", "-n", "rock")

        result = invoke("tag", "edit", "rock", "-c", "genre")

        assert result.exit_code == 0

    def test_tag_edit_no_option_fails(self, invoke):
        invoke("tag", "create", "-n", "rock")

        result = invoke("tag", "edit", "rock")

        assert result.exit_code != 0
        assert "Provide at least one option" in result.output

    def test_tag_edit_name_multiple_tags_fails(self, invoke):
        invoke("tag", "create", "-n", "rock")
        invoke("tag", "create", "-n", "jazz")

        result = invoke("tag", "edit", "rock", "jazz", "-n", "newname")

        assert result.exit_code != 0
        assert "--name can't be present when multiple tags" in result.output

    def test_tag_edit_set_and_clear_category_fails(self, invoke):
        invoke("tag", "create", "-n", "rock")

        result = invoke("tag", "edit", "rock", "-c", "genre", "--clear-category")

        assert result.exit_code != 0
        assert "Can't both set and clear" in result.output

    def test_tag_edit_clear_category(self, invoke):
        invoke("tag", "create", "-n", "rock", "-c", "genre")

        result = invoke("tag", "edit", "rock", "--clear-category")

        assert result.exit_code == 0

        # Verify category is cleared
        ls_result = invoke("tag", "ls", "-l")
        assert "rock" in ls_result.output
        assert "genre" not in ls_result.output

    def test_tag_delete(self, invoke):
        invoke("tag", "create", "-n", "rock")

        result = invoke("tag", "delete", "rock", input="y\n")

        assert result.exit_code == 0

    def test_tag_delete_abort(self, invoke):
        invoke("tag", "create", "-n", "rock")

        result = invoke("tag", "delete", "rock", input="n\n")

        assert result.exit_code != 0  # Aborted

    def test_tag_replace(self, invoke, tagged_file):
        result = invoke("tag", "replace", "rock", "-n", "jazz")

        assert result.exit_code == 0
