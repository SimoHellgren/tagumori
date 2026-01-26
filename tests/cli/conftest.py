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
