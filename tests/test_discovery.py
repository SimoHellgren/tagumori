import re
from pathlib import Path

import click
import pytest

from tagumori.discovery import (
    DB_NAME,
    POINTER,
    data_dir,
    discover_vault,
    new_db_dir,
    pointer_path,
    read_pointer,
    vault_db_path,
)


def write_pointer(directory: Path, text: str) -> Path:
    pointer = pointer_path(directory)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(text)
    return pointer


class TestDataDir:
    def test_uses_xdg_data_home(self, data_home):
        assert data_dir() == data_home

    @pytest.mark.parametrize("xdg", [None, ""], ids=["unset", "empty"])
    def test_falls_back_to_local_share(self, tmp_path, monkeypatch, xdg):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        if xdg is None:
            monkeypatch.delenv("XDG_DATA_HOME")
        else:
            monkeypatch.setenv("XDG_DATA_HOME", xdg)

        assert data_dir() == tmp_path / "home" / ".local/share/tagumori"


class TestVaultDbPath:
    def test_resolves_inside_the_data_dir(self, data_home):
        assert vault_db_path("tagumori-abc123") == (
            data_home / "tagumori-abc123" / DB_NAME
        )

    def test_does_not_require_the_db_to_exist(self, data_home):
        assert not vault_db_path("tagumori-abc123").exists()

    @pytest.mark.parametrize("bad_id", ["a/b", "/etc/passwd", ".", "../x"])
    def test_rejects_ids_that_are_not_a_single_path_component(self, bad_id):
        with pytest.raises(click.ClickException, match="Invalid vault id"):
            vault_db_path(bad_id)


class TestPointerPath:
    def test_is_inside_the_given_directory(self, tmp_path):
        assert pointer_path(tmp_path) == tmp_path / POINTER


class TestReadPointer:
    def test_returns_the_id(self, tmp_path):
        assert read_pointer(write_pointer(tmp_path, "tagumori-abc123")) == (
            "tagumori-abc123"
        )

    def test_strips_surrounding_whitespace(self, tmp_path):
        pointer = write_pointer(tmp_path, "  tagumori-abc123\n")

        assert read_pointer(pointer) == "tagumori-abc123"

    def test_missing_file(self, tmp_path):
        assert read_pointer(pointer_path(tmp_path)) is None

    @pytest.mark.parametrize("text", ["", "   \n"], ids=["empty", "whitespace"])
    def test_empty_pointer_is_none(self, tmp_path, text):
        assert read_pointer(write_pointer(tmp_path, text)) is None

    def test_directory_in_place_of_the_file(self, tmp_path):
        pointer_path(tmp_path).mkdir(parents=True)

        assert read_pointer(pointer_path(tmp_path)) is None


class TestDiscoverVault:
    def test_finds_the_pointer_in_the_start_directory(self, tmp_path, data_home):
        write_pointer(tmp_path, "tagumori-aaaaaa")

        assert discover_vault(tmp_path) == data_home / "tagumori-aaaaaa" / DB_NAME

    def test_finds_the_pointer_in_a_parent_directory(self, tmp_path, data_home):
        write_pointer(tmp_path, "tagumori-aaaaaa")
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)

        assert discover_vault(nested) == data_home / "tagumori-aaaaaa" / DB_NAME

    def test_nearest_pointer_wins(self, tmp_path, data_home):
        write_pointer(tmp_path, "tagumori-outer0")
        inner = tmp_path / "inner"
        write_pointer(inner, "tagumori-inner0")

        assert discover_vault(inner) == data_home / "tagumori-inner0" / DB_NAME

    def test_empty_pointer_is_skipped(self, tmp_path, data_home):
        write_pointer(tmp_path, "tagumori-outer0")
        inner = tmp_path / "inner"
        write_pointer(inner, "")

        assert discover_vault(inner) == data_home / "tagumori-outer0" / DB_NAME

    def test_returns_none_when_there_is_no_pointer(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()

        assert discover_vault(empty) is None

    def test_defaults_to_the_current_directory(
        self, tmp_path, data_home, monkeypatch
    ):
        write_pointer(tmp_path, "tagumori-aaaaaa")
        monkeypatch.chdir(tmp_path)

        assert discover_vault() == data_home / "tagumori-aaaaaa" / DB_NAME

    def test_does_not_check_that_the_db_exists(self, tmp_path):
        """Reporting a missing db is the caller's job (see LazyVault.path)."""
        write_pointer(tmp_path, "tagumori-aaaaaa")

        found = discover_vault(tmp_path)

        assert found is not None
        assert not found.exists()

    def test_invalid_id_in_the_pointer_is_an_error(self, tmp_path):
        write_pointer(tmp_path, "../x")

        with pytest.raises(click.ClickException, match="Invalid vault id"):
            discover_vault(tmp_path)


class TestNewDbDir:
    def test_creates_an_empty_directory_in_the_data_dir(self, data_home):
        created = new_db_dir()

        assert created.parent == data_home
        assert created.is_dir()
        assert list(created.iterdir()) == []

    def test_id_has_the_expected_shape(self):
        assert re.fullmatch(r"tagumori-[0-9a-f]{6}", new_db_dir().name)

    def test_creates_the_data_dir_when_missing(self, data_home):
        assert not data_home.exists()

        new_db_dir()

        assert data_home.is_dir()

    def test_each_call_makes_a_new_directory(self):
        assert new_db_dir() != new_db_dir()

    def test_retries_when_the_id_is_taken(self, data_home, monkeypatch):
        ids = iter(["aaaaaa", "aaaaaa", "bbbbbb"])
        monkeypatch.setattr("secrets.token_hex", lambda nbytes=None: next(ids))

        first, second = new_db_dir(), new_db_dir()

        assert first.name == "tagumori-aaaaaa"
        assert second.name == "tagumori-bbbbbb"
