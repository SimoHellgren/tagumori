import json
from dataclasses import fields
from pathlib import Path

import pytest

from tagumori.models import File, Query, Tag, TaggedFile


@pytest.mark.parametrize(
    "model,table", [(File, "file"), (Tag, "tag"), [Query, "query"]]
)
def test_model_matches_schema(conn, model, table):
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}

    assert cols == {f.name for f in fields(model)}


class TestFileFromRow:
    def test_converts_path_string_to_path_object(self, conn):
        conn.execute(
            "INSERT INTO file (path, inode, device) VALUES (?, ?, ?)",
            ("/tmp/song.mp3", 123, 456),
        )
        row = conn.execute("SELECT * FROM file").fetchone()

        file = File.from_row(row)

        assert file.path == Path("/tmp/song.mp3")
        assert isinstance(file.path, Path)
        assert file.inode == 123
        assert file.device == 456
        assert file.id == row["id"]

    def test_handles_null_inode_and_device(self, conn):
        conn.execute(
            "INSERT INTO file (path, inode, device) VALUES (?, NULL, NULL)",
            ("/tmp/song.mp3",),
        )
        row = conn.execute("SELECT * FROM file").fetchone()

        file = File.from_row(row)

        assert file.inode is None
        assert file.device is None


class TestTagFromRow:
    def test_converts_row_to_tag(self, conn):
        conn.execute(
            "INSERT INTO tag (name, category) VALUES (?, ?)", ("rock", "genre")
        )
        row = conn.execute("SELECT * FROM tag").fetchone()

        tag = Tag.from_row(row)

        assert tag.name == "rock"
        assert tag.category == "genre"
        assert tag.id == row["id"]

    def test_handles_null_category(self, conn):
        conn.execute("INSERT INTO tag (name) VALUES (?)", ("rock",))
        row = conn.execute("SELECT * FROM tag").fetchone()

        tag = Tag.from_row(row)

        assert tag.category is None


class TestQueryFromRow:
    def _insert(self, conn, **overrides):
        data = {
            "name": "my-query",
            "select_tags": json.dumps(["rock", "jazz"]),
            "exclude_tags": json.dumps(["blues"]),
            "pattern": r".*\.mp3",
            "ignore_case": 1,
            "invert_match": 0,
            "ignore_tag_case": 1,
        }
        data.update(overrides)
        conn.execute(
            """
            INSERT INTO query (
                name, select_tags, exclude_tags, pattern,
                ignore_case, invert_match, ignore_tag_case
            ) VALUES (:name, :select_tags, :exclude_tags, :pattern,
                      :ignore_case, :invert_match, :ignore_tag_case)
            """,
            data,
        )
        return conn.execute("SELECT * FROM query").fetchone()

    def test_parses_select_and_exclude_tags_from_json(self, conn):
        row = self._insert(conn)

        query = Query.from_row(row)

        assert query.select_tags == ("rock", "jazz")
        assert query.exclude_tags == ("blues",)

    def test_defaults_select_and_exclude_tags_to_empty_when_null(self, conn):
        row = self._insert(conn, select_tags=None, exclude_tags=None)

        query = Query.from_row(row)

        assert query.select_tags == ()
        assert query.exclude_tags == ()

    def test_defaults_pattern_when_null(self, conn):
        row = self._insert(conn, pattern=None)

        query = Query.from_row(row)

        assert query.pattern == r".*"

    def test_converts_integer_flags_to_bool(self, conn):
        row = self._insert(conn, ignore_case=1, invert_match=0, ignore_tag_case=1)

        query = Query.from_row(row)

        assert query.ignore_case is True
        assert query.invert_match is False
        assert query.ignore_tag_case is True


class TestTaggedFile:
    def test_path_proxies_to_file_path(self):
        file = File(id=1, path=Path("/tmp/song.mp3"), inode=None, device=None)

        tagged = TaggedFile(file)

        assert tagged.path == Path("/tmp/song.mp3")

    def test_tags_defaults_to_none(self):
        file = File(id=1, path=Path("/tmp/song.mp3"), inode=None, device=None)

        tagged = TaggedFile(file)

        assert tagged.tags is None
