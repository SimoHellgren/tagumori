from filetags.cli import cli


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
            cli, ["--vault", str(vault), "file", "info", str(sample_file)]
        )
        assert "guitar" in show_result.output
