from click.testing import CliRunner
from filetags.src.cli import cli


def test_ls(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["ls"])

    assert result.output == "file1\nfile2\n"


def test_ls_select(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["ls", "-s", "A"])

    assert result.output == "file1\n"

    result = cli_runner.invoke(cli, ["ls", "-s", "B"])

    assert result.output == "file1\nfile2\n"

    result = cli_runner.invoke(cli, ["ls", "-s", "B[b]"])

    assert result.output == "file2\n"


def test_ls_exclude(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["ls", "-e", "A"])

    assert result.output == "file2\n"

    result = cli_runner.invoke(cli, ["ls", "-e", "B"])

    assert result.output == ""

    result = cli_runner.invoke(cli, ["ls", "-e", "B[b]"])

    assert result.output == "file1\n"
