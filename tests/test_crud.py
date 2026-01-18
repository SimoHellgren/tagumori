from pathlib import Path

import pytest

from filetags import crud


class TestTagCRUD:
    def test_create(self, conn):
        row = crud.tag.create(conn, "rock", "genre")

        assert row["name"] == "rock"
        assert row["category"] == "genre"
        assert row["id"] is not None

    def test_create_without_category(self, conn):
        row = crud.tag.create(conn, "rock")

        assert row["name"] == "rock"
        assert row["category"] is None
        assert row["id"] is not None

    def test_get_by_name(self, conn):
        crud.tag.create(conn, "rock")

        row = crud.tag.get_by_name(conn, "rock")

        assert row["name"] == "rock"

    def test_get_by_name_not_found(self, conn):
        row = crud.tag.get_by_name(conn, "this doesn't exist!")

        assert row is None

    def test_get_many_by_name(self, conn):
        crud.tag.create(conn, "rock")
        crud.tag.create(conn, "opera")
        crud.tag.create(conn, "jazz")

        rows = crud.tag.get_many_by_name(conn, ["rock", "opera"])

        assert len(rows) == 2
        assert {"rock", "opera"} == {r["name"] for r in rows}

    def test_get_many_by_name_empty(self, conn):
        rows = crud.tag.get_many_by_name(conn, [])

        assert rows == []

    def test_get_many_by_name_missing(self, conn):
        crud.tag.create(conn, "rock")
        crud.tag.create(conn, "opera")

        rows = crud.tag.get_many_by_name(conn, ["rock", "jazz"])

        names = {r["name"] for r in rows}

        assert len(rows) == 1
        assert "rock" in names
        assert "opera" not in names
        assert "jazz" not in names

    def test_get_or_create_creates(self, conn):
        row = crud.tag.get_or_create(conn, "rock")

        assert row["name"] == "rock"

    def test_get_or_create_idempotent(self, conn):
        row1 = crud.tag.get_or_create(conn, "rock")
        row2 = crud.tag.get_or_create(conn, "rock")

        assert row1["id"] == row2["id"]

    def test_get_or_create_many(self, conn):
        rows = crud.tag.get_or_create_many(conn, ["rock", "jazz"])

        assert len(rows) == 2

    def test_get_or_create_many_idempotent(self, conn):
        rows1 = crud.tag.get_or_create_many(conn, ["rock", "jazz"])
        rows2 = crud.tag.get_or_create_many(conn, ["rock", "jazz"])

        ids1 = {r["id"] for r in rows1}
        ids2 = {r["id"] for r in rows2}
        assert ids1 == ids2

    def test_get_all(self, conn):
        crud.tag.create(conn, "rock")
        crud.tag.create(conn, "jazz")

        rows = crud.tag.get_all(conn)

        assert len(rows) == 2

    def test_get_all_empty(self, conn):
        rows = crud.tag.get_all(conn)

        assert rows == []

    def test_update_single(self, conn):
        crud.tag.create(conn, "rock")

        crud.tag.update(conn, ["rock"], {"category": "genre"})

        row = crud.tag.get_by_name(conn, "rock")
        assert row["category"] == "genre"

    def test_update_multiple(self, conn):
        crud.tag.create(conn, "rock")
        crud.tag.create(conn, "jazz")

        crud.tag.update(conn, ["rock", "jazz"], {"category": "genre"})

        for name in ["rock", "jazz"]:
            row = crud.tag.get_by_name(conn, name)
            assert row["category"] == "genre"

    def test_update_forbidden_column(self, conn):
        crud.tag.create(conn, "rock")

        with pytest.raises(ValueError, match="Forbidden column"):
            crud.tag.update(conn, ["rock"], {"id": 999})

    def test_delete(self, conn):
        row = crud.tag.create(conn, "rock")

        crud.tag.delete(conn, row["id"])

        assert crud.tag.get_by_name(conn, "rock") is None


class TestFileCRUD:
    def test_get_or_create(self, conn):
        row = crud.file.get_or_create(conn, Path("foo.txt"))

        assert row["id"] is not None

    def test_get_or_create_idempotent(self, conn):
        row1 = crud.file.get_or_create(conn, Path("foo.txt"))
        row2 = crud.file.get_or_create(conn, Path("foo.txt"))

        assert row1["id"] == row2["id"]

    def test_get_by_path(self, conn):
        crud.file.get_or_create(conn, Path("foo.txt"))

        row = crud.file.get_by_path(conn, Path("foo.txt"))

        assert row is not None

    def test_get_by_path_not_found(self, conn):
        row = crud.file.get_by_path(conn, Path("nonexistent.txt"))

        assert row is None

    def test_get_many_by_path(self, conn):
        crud.file.get_or_create(conn, Path("a.txt"))
        crud.file.get_or_create(conn, Path("b.txt"))

        rows = crud.file.get_many_by_path(conn, [Path("a.txt"), Path("b.txt")])

        assert len(rows) == 2

    def test_get_or_create_many(self, conn):
        rows = crud.file.get_or_create_many(conn, [Path("a.txt"), Path("b.txt")])

        assert len(rows) == 2

    def test_delete(self, conn):
        row = crud.file.get_or_create(conn, Path("foo.txt"))

        crud.file.delete(conn, row["id"])

        assert crud.file.get_by_path(conn, Path("foo.txt")) is None


class TestFileTag:
    @pytest.fixture
    def file_and_tag(self, conn):
        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        tag_row = crud.tag.create(conn, "rock")
        return file_row["id"], tag_row["id"]

    def test_attach(self, conn, file_and_tag):
        file_id, tag_id = file_and_tag

        file_tag_id = crud.file_tag.attach(conn, file_id, tag_id)

        assert file_tag_id is not None

    def test_attach_idempotent(self, conn, file_and_tag):
        file_id, tag_id = file_and_tag

        id1 = crud.file_tag.attach(conn, file_id, tag_id)
        id2 = crud.file_tag.attach(conn, file_id, tag_id)

        assert id1 == id2

    def test_attach_with_parent(self, conn, file_and_tag):
        file_id, tag_id = file_and_tag
        child_tag = crud.tag.create(conn, "classic")

        parent_id = crud.file_tag.attach(conn, file_id, tag_id)
        child_id = crud.file_tag.attach(conn, file_id, child_tag["id"], parent_id)

        assert child_id is not None
        assert child_id != parent_id

    def test_detach(self, conn, file_and_tag):
        file_id, tag_id = file_and_tag
        file_tag_id = crud.file_tag.attach(conn, file_id, tag_id)

        crud.file_tag.detach(conn, file_tag_id)

        rows = crud.file_tag.get_by_file_id(conn, file_id)
        assert rows == []

    def test_get_by_file_id(self, conn, file_and_tag):
        file_id, tag_id = file_and_tag
        crud.file_tag.attach(conn, file_id, tag_id)

        rows = crud.file_tag.get_by_file_id(conn, file_id)

        assert len(rows) == 1
        assert rows[0]["name"] == "rock"

    def test_drop_for_file(self, conn, file_and_tag):
        file_id, tag_id = file_and_tag
        crud.file_tag.attach(conn, file_id, tag_id)

        crud.file_tag.drop_for_file(conn, file_id)

        rows = crud.file_tag.get_by_file_id(conn, file_id)
        assert rows == []

    def test_replace(self, conn, file_and_tag):
        file_id, tag_id = file_and_tag
        new_tag = crud.tag.create(conn, "jazz")
        crud.file_tag.attach(conn, file_id, tag_id)

        crud.file_tag.replace(conn, tag_id, new_tag["id"])

        rows = crud.file_tag.get_by_file_id(conn, file_id)
        assert rows[0]["name"] == "jazz"


class TestTagalong:
    @pytest.fixture
    def two_tags(self, conn):
        t1 = crud.tag.create(conn, "rock")
        t2 = crud.tag.create(conn, "guitar")
        return t1["id"], t2["id"]

    def test_create(self, conn, two_tags):
        source_id, target_id = two_tags

        crud.tagalong.create(conn, source_id, target_id)

        rows = crud.tagalong.get_all_names(conn)
        assert len(rows) == 1
        assert rows[0][0] == "rock"
        assert rows[0][1] == "guitar"

    def test_create_idempotent(self, conn, two_tags):
        source_id, target_id = two_tags

        crud.tagalong.create(conn, source_id, target_id)
        crud.tagalong.create(conn, source_id, target_id)

        rows = crud.tagalong.get_all_names(conn)
        assert len(rows) == 1

    def test_delete(self, conn, two_tags):
        source_id, target_id = two_tags
        crud.tagalong.create(conn, source_id, target_id)

        crud.tagalong.delete(conn, source_id, target_id)

        rows = crud.tagalong.get_all_names(conn)
        assert rows == []

    def test_apply(self, conn, two_tags):
        source_id, target_id = two_tags
        crud.tagalong.create(conn, source_id, target_id)

        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        crud.file_tag.attach(conn, file_row["id"], source_id)

        crud.tagalong.apply(conn, [file_row["id"]])

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        tag_names = {r["name"] for r in rows}
        assert tag_names == {"rock", "guitar"}

    def test_apply_transitive(self, conn):
        """Test that tagalongs are applied transitively: A->B->C"""
        a = crud.tag.create(conn, "A")
        b = crud.tag.create(conn, "B")
        c = crud.tag.create(conn, "C")

        crud.tagalong.create(conn, a["id"], b["id"])
        crud.tagalong.create(conn, b["id"], c["id"])

        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        crud.file_tag.attach(conn, file_row["id"], a["id"])

        crud.tagalong.apply(conn, [file_row["id"]])

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        tag_names = {r["name"] for r in rows}
        assert tag_names == {"A", "B", "C"}
