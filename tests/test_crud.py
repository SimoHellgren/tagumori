from pathlib import Path

import pytest

from filetags import crud
from filetags.crud.file import _get_inode_and_device


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
    def test_inode_utility_real_file(self, tmp_path):
        file = tmp_path / "real.txt"
        file.touch()  # touch to make it real

        inode, device = _get_inode_and_device(file)

        assert inode is not None
        assert device is not None

    def test_inode_utility_fake_file(self):
        file = Path("fake.txt")

        inode, device = _get_inode_and_device(file)

        assert inode is None
        assert device is None

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

    def test_get_or_create_stores_inode_and_device(self, conn, tmp_path):
        """When adding a real file, inode and device should be stored."""
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")

        crud.file.get_or_create(conn, real_file)

        # Re-fetch to get all columns
        fetched = crud.file.get_by_path(conn, real_file)
        stat = real_file.stat()

        assert fetched["inode"] == stat.st_ino
        assert fetched["device"] == stat.st_dev

    def test_get_or_create_many_stores_inode_and_device(self, conn, tmp_path):
        """When adding multiple real files, inode and device should be stored for each."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"
        file1.write_text("a")
        file2.write_text("b")

        crud.file.get_or_create_many(conn, [file1, file2])

        for path in [file1, file2]:
            fetched = crud.file.get_by_path(conn, path)
            stat = path.stat()
            assert fetched["inode"] == stat.st_ino
            assert fetched["device"] == stat.st_dev

    def test_inode_device_null_for_nonexistent_path(self, conn):
        """For paths that don't exist on disk, inode/device should be null."""
        crud.file.get_or_create(conn, Path("nonexistent.txt"))

        fetched = crud.file.get_by_path(conn, Path("nonexistent.txt").resolve())

        assert fetched["inode"] is None
        assert fetched["device"] is None

    def test_get_or_create_stores_absolute_path(self, conn, tmp_path):
        """Paths should be stored as absolute (resolved) paths."""
        real_file = tmp_path / "file.txt"
        real_file.write_text("content")

        crud.file.get_or_create(conn, real_file)

        fetched = crud.file.get_by_path(conn, real_file)

        assert fetched["path"] == str(real_file.resolve())

    def test_get_or_create_resolves_relative_path(self, conn, tmp_path, monkeypatch):
        """Relative paths should be resolved to absolute before storing."""
        # Change to tmp_path so relative paths resolve there
        monkeypatch.chdir(tmp_path)

        real_file = tmp_path / "relative_test.txt"
        real_file.write_text("content")

        # Pass a relative path
        crud.file.get_or_create(conn, Path("relative_test.txt"))

        # Should be stored as absolute
        fetched = crud.file.get_by_path(conn, Path("relative_test.txt").resolve())

        assert fetched is not None
        assert fetched["path"] == str(real_file.resolve())
        assert Path(fetched["path"]).is_absolute()

    def test_get_or_create_many_stores_absolute_paths(self, conn, tmp_path):
        """Multiple paths should all be stored as absolute."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"
        file1.write_text("a")
        file2.write_text("b")

        crud.file.get_or_create_many(conn, [file1, file2])

        for path in [file1, file2]:
            fetched = crud.file.get_by_path(conn, path.resolve())
            assert fetched is not None
            assert fetched["path"] == str(path.resolve())
            assert Path(fetched["path"]).is_absolute()


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

    def test_circular_tagalong_two_nodes(self, conn):
        """A -> B -> A should not loop infinitely."""
        a = crud.tag.create(conn, "A")
        b = crud.tag.create(conn, "B")

        crud.tagalong.create(conn, a["id"], b["id"])
        crud.tagalong.create(conn, b["id"], a["id"])

        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        crud.file_tag.attach(conn, file_row["id"], a["id"])

        # Should complete without hanging
        crud.tagalong.apply(conn, [file_row["id"]])

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        tag_names = {r["name"] for r in rows}
        assert tag_names == {"A", "B"}

    def test_circular_tagalong_three_nodes(self, conn):
        """A -> B -> C -> A should not loop infinitely."""
        a = crud.tag.create(conn, "A")
        b = crud.tag.create(conn, "B")
        c = crud.tag.create(conn, "C")

        crud.tagalong.create(conn, a["id"], b["id"])
        crud.tagalong.create(conn, b["id"], c["id"])
        crud.tagalong.create(conn, c["id"], a["id"])

        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        crud.file_tag.attach(conn, file_row["id"], a["id"])

        # Should complete without hanging
        crud.tagalong.apply(conn, [file_row["id"]])

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        tag_names = {r["name"] for r in rows}
        assert tag_names == {"A", "B", "C"}

    def test_self_referential_tagalong(self, conn):
        """A -> A should not cause issues."""
        a = crud.tag.create(conn, "A")

        crud.tagalong.create(conn, a["id"], a["id"])

        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        crud.file_tag.attach(conn, file_row["id"], a["id"])

        # Should complete without hanging
        crud.tagalong.apply(conn, [file_row["id"]])

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        tag_names = {r["name"] for r in rows}
        assert tag_names == {"A"}


class TestCascadeDeletes:
    """Test that foreign key cascades work correctly."""

    def test_delete_file_cascades_to_file_tag(self, conn):
        """Deleting a file should delete its file_tags."""
        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        tag_row = crud.tag.create(conn, "rock")
        crud.file_tag.attach(conn, file_row["id"], tag_row["id"])

        crud.file.delete(conn, file_row["id"])

        # file_tag should be gone
        rows = conn.execute("SELECT * FROM file_tag").fetchall()
        assert rows == []

    def test_delete_tag_cascades_to_file_tag(self, conn):
        """Deleting a tag should delete its file_tags."""
        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        tag_row = crud.tag.create(conn, "rock")
        crud.file_tag.attach(conn, file_row["id"], tag_row["id"])

        crud.tag.delete(conn, tag_row["id"])

        # file_tag should be gone
        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        assert rows == []
        # file should still exist
        assert crud.file.get_by_path(conn, Path("test.txt")) is not None

    def test_delete_tag_cascades_to_tagalong(self, conn):
        """Deleting a tag should delete its tagalong relationships."""
        t1 = crud.tag.create(conn, "rock")
        t2 = crud.tag.create(conn, "guitar")
        crud.tagalong.create(conn, t1["id"], t2["id"])

        crud.tag.delete(conn, t1["id"])

        rows = crud.tagalong.get_all_names(conn)
        assert rows == []

    def test_delete_parent_file_tag_cascades_to_children(self, conn):
        """Deleting a parent file_tag should delete its children."""
        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        parent_tag = crud.tag.create(conn, "genre")
        child_tag = crud.tag.create(conn, "rock")
        grandchild_tag = crud.tag.create(conn, "classic")

        parent_ft_id = crud.file_tag.attach(conn, file_row["id"], parent_tag["id"])
        child_ft_id = crud.file_tag.attach(
            conn, file_row["id"], child_tag["id"], parent_ft_id
        )
        crud.file_tag.attach(conn, file_row["id"], grandchild_tag["id"], child_ft_id)

        # Delete parent - should cascade to child and grandchild
        crud.file_tag.detach(conn, parent_ft_id)

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        assert rows == []

    def test_delete_child_file_tag_preserves_parent(self, conn):
        """Deleting a child file_tag should preserve the parent."""
        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        parent_tag = crud.tag.create(conn, "genre")
        child_tag = crud.tag.create(conn, "rock")

        parent_ft_id = crud.file_tag.attach(conn, file_row["id"], parent_tag["id"])
        child_ft_id = crud.file_tag.attach(
            conn, file_row["id"], child_tag["id"], parent_ft_id
        )

        crud.file_tag.detach(conn, child_ft_id)

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        assert len(rows) == 1
        assert rows[0]["name"] == "genre"

    def test_delete_child_file_tag_cascades_to_grandchildren(self, conn):
        """Deleting a child file_tag should delete its children but preserve parent."""
        file_row = crud.file.get_or_create(conn, Path("test.txt"))
        parent_tag = crud.tag.create(conn, "genre")
        child_tag = crud.tag.create(conn, "rock")
        grandchild_tag = crud.tag.create(conn, "classic")

        parent_ft_id = crud.file_tag.attach(conn, file_row["id"], parent_tag["id"])
        child_ft_id = crud.file_tag.attach(
            conn, file_row["id"], child_tag["id"], parent_ft_id
        )
        crud.file_tag.attach(conn, file_row["id"], grandchild_tag["id"], child_ft_id)

        # Delete child - should cascade to grandchild but preserve parent
        crud.file_tag.detach(conn, child_ft_id)

        rows = crud.file_tag.get_by_file_id(conn, file_row["id"])
        assert len(rows) == 1
        assert rows[0]["name"] == "genre"


class TestFileTagPaths:
    """Tests for resolve_path."""

    @pytest.fixture
    def file_with_tag_tree(self, conn):
        """
        Creates a file with tag tree: genre -> rock -> classic
        """
        file_row = crud.file.get_or_create(conn, Path("song.mp3"))
        genre = crud.tag.create(conn, "genre")
        rock = crud.tag.create(conn, "rock")
        classic = crud.tag.create(conn, "classic")

        genre_ft = crud.file_tag.attach(conn, file_row["id"], genre["id"])
        rock_ft = crud.file_tag.attach(conn, file_row["id"], rock["id"], genre_ft)
        classic_ft = crud.file_tag.attach(conn, file_row["id"], classic["id"], rock_ft)

        return {
            "file_id": file_row["id"],
            "file_tag_ids": {"genre": genre_ft, "rock": rock_ft, "classic": classic_ft},
        }

    def test_resolve_path_full(self, conn, file_with_tag_tree):
        """resolve_path returns the file_tag id of the last node in the path."""
        file_id = file_with_tag_tree["file_id"]
        path = ("genre", "rock", "classic")

        result = crud.file_tag.resolve_path(conn, file_id, path)

        assert result == file_with_tag_tree["file_tag_ids"]["classic"]

    def test_resolve_path_partial(self, conn, file_with_tag_tree):
        """resolve_path works for partial paths."""
        file_id = file_with_tag_tree["file_id"]
        path = ("genre", "rock")

        result = crud.file_tag.resolve_path(conn, file_id, path)

        assert result == file_with_tag_tree["file_tag_ids"]["rock"]

    def test_resolve_path_root_only(self, conn, file_with_tag_tree):
        """resolve_path works for root-only path."""
        file_id = file_with_tag_tree["file_id"]
        path = ("genre",)

        result = crud.file_tag.resolve_path(conn, file_id, path)

        assert result == file_with_tag_tree["file_tag_ids"]["genre"]

    def test_resolve_path_not_found(self, conn, file_with_tag_tree):
        """resolve_path returns None if path doesn't exist."""
        file_id = file_with_tag_tree["file_id"]
        path = ("genre", "jazz")  # jazz doesn't exist

        result = crud.file_tag.resolve_path(conn, file_id, path)

        assert result is None

    def test_resolve_path_wrong_order(self, conn, file_with_tag_tree):
        """resolve_path returns None if path is in wrong order."""
        file_id = file_with_tag_tree["file_id"]
        path = ("rock", "genre")  # wrong order

        result = crud.file_tag.resolve_path(conn, file_id, path)

        assert result is None

    def test_resolve_path_empty(self, conn, file_with_tag_tree):
        """resolve_path with empty path returns None."""
        file_id = file_with_tag_tree["file_id"]

        result = crud.file_tag.resolve_path(conn, file_id, ())

        assert result is None
