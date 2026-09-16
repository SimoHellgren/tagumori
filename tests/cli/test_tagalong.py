class TestTagalongCommands:
    def test_tagalong_add(self, invoke):
        result = invoke("tagalong", "add", "-t", "rock", "-ta", "guitar")

        assert result.exit_code == 0

    def test_tagalong_ls(self, invoke):
        invoke("tagalong", "add", "-t", "rock", "-ta", "guitar")

        result = invoke("tagalong", "ls")

        assert result.exit_code == 0
        assert "rock" in result.output
        assert "guitar" in result.output
        assert "->" in result.output

    def test_tagalong_remove(self, invoke):
        invoke("tagalong", "add", "-t", "rock", "-ta", "guitar")

        result = invoke("tagalong", "remove", "-t", "rock", "-ta", "guitar")

        assert result.exit_code == 0

        # Verify it's gone
        ls_result = invoke("tagalong", "ls")
        assert "rock" not in ls_result.output

    def test_tagalong_apply(self, invoke, sample_file):
        invoke("tagalong", "add", "-t", "rock", "-ta", "guitar")
        invoke("add", "-f", str(sample_file), "-t", "rock", "--no-tagalongs")

        result = invoke("tagalong", "apply", "-f", str(sample_file))

        assert result.exit_code == 0

        # Verify tagalong was applied
        show_result = invoke("file", "info", str(sample_file))
        assert "guitar" in show_result.output
