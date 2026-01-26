import pytest
from click.testing import CliRunner

from filetags.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def vault(tmp_path):
    """Creates a temporary vault file and returns its path."""
    vault_path = tmp_path / "test_vault.db"
    runner = CliRunner()
    runner.invoke(cli, ["db", "init", str(vault_path)])
    return vault_path


@pytest.fixture
def sample_file(tmp_path):
    """Creates a temporary file to tag."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def tagged_file(runner, vault, sample_file):
    """A sample file already tagged with 'rock'."""
    runner.invoke(
        cli, ["--vault", str(vault), "add", "-f", str(sample_file), "-t", "rock"]
    )
    return sample_file


@pytest.fixture
def sample_files(tmp_path):
    """Creates two temporary files for multi-file tests."""
    files = [tmp_path / "file1.txt", tmp_path / "file2.txt"]
    for f in files:
        f.write_text("content")
    return files
