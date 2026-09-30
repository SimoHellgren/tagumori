from pathlib import Path

import pytest

import tagumori.service
from tagumori.crud.file import _get_inode_and_device
from tests.helpers import not_none


class TestTagCRUD:
    def test_create(self, vault):
        row = vault.tags.create("rock", "genre")

        assert row.name == "rock"
        assert row.category == "genre"
        assert row.id is not None

    def test_create_without_category(self, vault):
        row = vault.tags.create("rock")

        assert row.name == "rock"
        assert row.category is None
        assert row.id is not None

    def test_get_by_name(self, vault):
        vault.tags.create("rock")

        row = not_none(vault.tags.get_by_name("rock"))

        assert row.name == "rock"

    def test_get_by_name_not_found(self, vault):
        row = vault.tags.get_by_name("this doesn't exist!")

        assert row is None

    def test_get_many_by_name(self, vault):
        vault.tags.create("rock")
        vault.tags.create("opera")
        vault.tags.create("jazz")

        rows = vault.tags.get_many_by_name(["rock", "opera"])

        assert len(rows) == 2
        assert {"rock", "opera"} == {r.name for r in rows}

    def test_get_many_by_name_empty(self, vault):
        rows = vault.tags.get_many_by_name([])

        assert rows == []

    def test_get_many_by_name_missing(self, vault):
        vault.tags.create("rock")
        vault.tags.create("opera")

        rows = vault.tags.get_many_by_name(["rock", "jazz"])

        names = {r.name for r in rows}

        assert len(rows) == 1
        assert "rock" in names
        assert "opera" not in names
        assert "jazz" not in names

    def test_get_or_create_creates(self, vault):
        row = vault.tags.get_or_create("rock")

        assert row.name == "rock"

    def test_get_or_create_idempotent(self, vault):
        row1 = vault.tags.get_or_create("rock")
        row2 = vault.tags.get_or_create("rock")

        assert row1.id == row2.id

    def test_get_or_create_many(self, vault):
        rows = vault.tags.get_or_create_many(["rock", "jazz"])

        assert len(rows) == 2

    def test_get_or_create_many_idempotent(self, vault):
        rows1 = vault.tags.get_or_create_many(["rock", "jazz"])
        rows2 = vault.tags.get_or_create_many(["rock", "jazz"])

        ids1 = {r.id for r in rows1}
        ids2 = {r.id for r in rows2}
        assert ids1 == ids2

    def test_get_all(self, vault):
        vault.tags.create("rock")
        vault.tags.create("jazz")

        rows = vault.tags.get_all()

        assert len(rows) == 2

    def test_get_all_empty(self, vault):
        rows = vault.tags.get_all()

        assert rows == []

    def test_update_single(self, vault):
        vault.tags.create("rock")

        vault.tags.update(["rock"], {"category": "genre"})

        row = not_none(vault.tags.get_by_name("rock"))
        assert row.category == "genre"

    def test_update_multiple(self, vault):
        vault.tags.create("rock")
        vault.tags.create("jazz")

        vault.tags.update(["rock", "jazz"], {"category": "genre"})

        for name in ["rock", "jazz"]:
            row = not_none(vault.tags.get_by_name(name))
            assert row.category == "genre"

    def test_update_forbidden_column(self, vault):
        vault.tags.create("rock")

        with pytest.raises(ValueError, match="Forbidden column"):
            vault.tags.update(["rock"], {"id": 999})

    def test_delete(self, vault):
        row = vault.tags.create("rock")

        vault.tags.delete(row.id)

        assert vault.tags.get_by_name("rock") is None


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

    def test_get_or_create(self, vault):
        row = vault.files.get_or_create(Path("foo.txt"))

        assert row.id is not None

    def test_get_or_create_idempotent(self, vault):
        row1 = vault.files.get_or_create(Path("foo.txt"))
        row2 = vault.files.get_or_create(Path("foo.txt"))

        assert row1.id == row2.id

    def test_get_by_path(self, vault):
        vault.files.get_or_create(Path("foo.txt"))

        row = vault.files.get_by_path(Path("foo.txt"))

        assert row is not None

    def test_get_by_path_not_found(self, vault):
        row = vault.files.get_by_path(Path("nonexistent.txt"))

        assert row is None

    def test_get_many_by_path(self, vault):
        vault.files.get_or_create(Path("a.txt"))
        vault.files.get_or_create(Path("b.txt"))

        rows = vault.files.get_many_by_path([Path("a.txt"), Path("b.txt")])

        assert len(rows) == 2

    def test_get_or_create_many(self, vault):
        rows = vault.files.get_or_create_many([Path("a.txt"), Path("b.txt")])

        assert len(rows) == 2

    def test_delete(self, vault):
        row = vault.files.get_or_create(Path("foo.txt"))

        vault.files.delete(row.id)

        assert vault.files.get_by_path(Path("foo.txt")) is None

    def test_get_or_create_stores_inode_and_device(self, vault, tmp_path):
        """When adding a real file, inode and device should be stored."""
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")

        vault.files.get_or_create(real_file)

        # Re-fetch to get all columns
        fetched = not_none(vault.files.get_by_path(real_file))
        stat = real_file.stat()

        assert fetched.inode == stat.st_ino
        assert fetched.device == stat.st_dev

    def test_get_or_create_many_stores_inode_and_device(self, vault, tmp_path):
        """When adding multiple real files, inode and device should be stored for each."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"
        file1.write_text("a")
        file2.write_text("b")

        vault.files.get_or_create_many([file1, file2])

        for path in [file1, file2]:
            fetched = not_none(vault.files.get_by_path(path))
            stat = path.stat()
            assert fetched.inode == stat.st_ino
            assert fetched.device == stat.st_dev

    def test_inode_device_null_for_nonexistent_path(self, vault):
        """For paths that don't exist on disk, inode/device should be null."""
        vault.files.get_or_create(Path("nonexistent.txt"))

        fetched = not_none(
            vault.files.get_by_path(Path("nonexistent.txt").resolve())
        )

        assert fetched.inode is None
        assert fetched.device is None

    def test_get_or_create_stores_absolute_path(self, vault, tmp_path):
        """Paths should be stored as absolute (resolved) paths."""
        real_file = tmp_path / "file.txt"
        real_file.write_text("content")

        vault.files.get_or_create(real_file)

        fetched = not_none(vault.files.get_by_path(real_file))

        assert fetched.path == real_file.resolve()

    def test_get_or_create_resolves_relative_path(self, vault, tmp_path, monkeypatch):
        """Relative paths should be resolved to absolute before storing."""
        # Change to tmp_path so relative paths resolve there
        monkeypatch.chdir(tmp_path)

        real_file = tmp_path / "relative_test.txt"
        real_file.write_text("content")

        # Pass a relative path
        vault.files.get_or_create(Path("relative_test.txt"))

        # Should be stored as absolute
        fetched = vault.files.get_by_path(Path("relative_test.txt").resolve())

        assert fetched is not None
        assert fetched.path == real_file.resolve()
        assert fetched.path.is_absolute()

    def test_get_or_create_many_stores_absolute_paths(self, vault, tmp_path):
        """Multiple paths should all be stored as absolute."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"
        file1.write_text("a")
        file2.write_text("b")

        vault.files.get_or_create_many([file1, file2])

        for path in [file1, file2]:
            fetched = vault.files.get_by_path(path.resolve())
            assert fetched is not None
            assert fetched.path == path.resolve()
            assert fetched.path.is_absolute()


class TestFileTag:
    @pytest.fixture
    def file_and_tag(self, vault, make_tag):
        file_row = vault.files.get_or_create(Path("test.txt"))
        tag_row = make_tag()
        return file_row.id, tag_row.id

    def test_attach(self, vault, file_and_tag):
        file_id, tag_id = file_and_tag

        file_tag_id = vault.file_tags.attach(file_id, tag_id)

        assert file_tag_id is not None

    def test_attach_idempotent(self, vault, file_and_tag):
        file_id, tag_id = file_and_tag

        id1 = vault.file_tags.attach(file_id, tag_id)
        id2 = vault.file_tags.attach(file_id, tag_id)

        assert id1 == id2

    def test_attach_with_parent(self, vault, file_and_tag):
        file_id, tag_id = file_and_tag
        child_tag = vault.tags.create("classic")

        parent_id = vault.file_tags.attach(file_id, tag_id)
        child_id = vault.file_tags.attach(file_id, child_tag.id, parent_id)

        assert child_id is not None
        assert child_id != parent_id

    def test_detach(self, vault, file_and_tag):
        file_id, tag_id = file_and_tag
        file_tag_id = vault.file_tags.attach(file_id, tag_id)

        vault.file_tags.detach(file_tag_id)

        rows = tagumori.service.get_file_tag_nodes(vault, [file_id])
        assert rows == []

    def test_get_by_file_id(self, vault, file_and_tag):
        file_id, tag_id = file_and_tag
        vault.file_tags.attach(file_id, tag_id)

        rows = tagumori.service.get_file_tag_nodes(vault, [file_id])

        assert len(rows) == 1
        assert rows[0].tag_name == "rock"

    def test_drop_for_file(self, vault, file_and_tag):
        file_id, tag_id = file_and_tag
        vault.file_tags.attach(file_id, tag_id)

        vault.file_tags.drop_for_file(file_id)

        rows = tagumori.service.get_file_tag_nodes(vault, [file_id])
        assert rows == []

    def test_replace(self, vault, file_and_tag):
        file_id, tag_id = file_and_tag
        new_tag = vault.tags.create("jazz")
        vault.file_tags.attach(file_id, tag_id)

        vault.file_tags.replace(tag_id, new_tag.id)

        rows = tagumori.service.get_file_tag_nodes(vault, [file_id])
        assert rows[0].tag_name == "jazz"


class TestTagalong:
    @pytest.fixture
    def two_tags(self, make_tag) -> tuple[int, int]:
        t1 = make_tag("rock")
        t2 = make_tag("guitar")
        return t1.id, t2.id

    def test_create(self, vault, two_tags):
        source_id, target_id = two_tags

        vault.tagalongs.create(source_id, target_id)

        rows = tagumori.service.list_tagalong_names(vault)
        assert len(rows) == 1
        assert rows[0].tag_name == "rock"
        assert rows[0].tagalong_name == "guitar"

    def test_create_idempotent(self, vault, two_tags):
        source_id, target_id = two_tags

        vault.tagalongs.create(source_id, target_id)
        vault.tagalongs.create(source_id, target_id)

        rows = tagumori.service.list_tagalong_names(vault)
        assert len(rows) == 1

    def test_delete(self, vault, two_tags):
        source_id, target_id = two_tags
        vault.tagalongs.create(source_id, target_id)

        vault.tagalongs.delete(source_id, target_id)

        rows = tagumori.service.list_tagalong_names(vault)
        assert rows == []

    def test_apply(self, vault, two_tags):
        source_id, target_id = two_tags
        vault.tagalongs.create(source_id, target_id)

        file_row = vault.files.get_or_create(Path("test.txt"))
        vault.file_tags.attach(file_row.id, source_id)

        vault.tagalongs.apply([file_row.id])

        rows = tagumori.service.get_file_tag_nodes(vault, [file_row.id])
        tag_names = {r.tag_name for r in rows}
        assert tag_names == {"rock", "guitar"}

    def test_apply_transitive(self, vault):
        """Test that tagalongs are applied transitively: A->B->C"""
        a = vault.tags.create("A")
        b = vault.tags.create("B")
        c = vault.tags.create("C")

        vault.tagalongs.create(a.id, b.id)
        vault.tagalongs.create(b.id, c.id)

        file_row = vault.files.get_or_create(Path("test.txt"))
        vault.file_tags.attach(file_row.id, a.id)

        vault.tagalongs.apply([file_row.id])

        rows = tagumori.service.get_file_tag_nodes(vault, [file_row.id])
        tag_names = {r.tag_name for r in rows}
        assert tag_names == {"A", "B", "C"}

    @pytest.mark.parametrize(
        "names, edges",
        [
            pytest.param(["A", "B"], [("A", "B"), ("B", "A")], id="two_node_cycle"),
            pytest.param(
                ["A", "B", "C"],
                [("A", "B"), ("B", "C"), ("C", "A")],
                id="three_node_cycle",
            ),
            pytest.param(["A"], [("A", "A")], id="self_referential"),
        ],
    )
    def test_circular_tagalong_terminates(self, vault, names, edges):
        """A cycle in the tagalong graph must not cause apply() to loop
        infinitely, and should still resolve to every tag in the cycle."""
        tags = {name: vault.tags.create(name) for name in names}
        for source, target in edges:
            vault.tagalongs.create(tags[source].id, tags[target].id)

        file_row = vault.files.get_or_create(Path("test.txt"))
        vault.file_tags.attach(file_row.id, tags[names[0]].id)

        # Should complete without hanging
        vault.tagalongs.apply([file_row.id])

        rows = tagumori.service.get_file_tag_nodes(vault, [file_row.id])
        tag_names = {r.tag_name for r in rows}
        assert tag_names == set(names)


class TestCascadeDeletes:
    """Test that foreign key cascades work correctly."""

    def test_delete_file_cascades_to_file_tag(self, vault):
        """Deleting a file should delete its file_tags."""
        file_row = vault.files.get_or_create(Path("test.txt"))
        tag_row = vault.tags.create("rock")
        vault.file_tags.attach(file_row.id, tag_row.id)

        vault.files.delete(file_row.id)

        # file_tag should be gone
        rows = vault.conn.execute("SELECT * FROM file_tag").fetchall()
        assert rows == []

    def test_delete_tag_cascades_to_file_tag(self, vault):
        """Deleting a tag should delete its file_tags."""
        file_row = vault.files.get_or_create(Path("test.txt"))
        tag_row = vault.tags.create("rock")
        vault.file_tags.attach(file_row.id, tag_row.id)

        vault.tags.delete(tag_row.id)

        # file_tag should be gone
        rows = tagumori.service.get_file_tag_nodes(vault, [file_row.id])
        assert rows == []
        # file should still exist
        assert vault.files.get_by_path(Path("test.txt")) is not None

    def test_delete_tag_cascades_to_tagalong(self, vault):
        """Deleting a tag should delete its tagalong relationships."""
        t1 = vault.tags.create("rock")
        t2 = vault.tags.create("guitar")
        vault.tagalongs.create(t1.id, t2.id)

        vault.tags.delete(t1.id)

        rows = tagumori.service.list_tagalong_names(vault)
        assert rows == []

    @pytest.mark.parametrize(
        "tag_names, detach_name, expected_remaining",
        [
            pytest.param(
                ("genre", "rock", "classic"),
                "genre",
                [],
                id="delete_parent_cascades_to_children_and_grandchildren",
            ),
            pytest.param(
                ("genre", "rock"),
                "rock",
                ["genre"],
                id="delete_child_preserves_parent",
            ),
            pytest.param(
                ("genre", "rock", "classic"),
                "rock",
                ["genre"],
                id="delete_child_cascades_to_grandchildren_preserves_parent",
            ),
        ],
    )
    def test_detach_cascades_down_the_tree(
        self, vault, make_tagged_file, tag_names, detach_name, expected_remaining
    ):
        """Detaching a file_tag should cascade to its descendants, while
        leaving its ancestors (and siblings) untouched."""
        fid = make_tagged_file("test.txt", [tag_names])
        rows = tagumori.service.get_file_tag_nodes(vault, [fid])
        ft_id_by_name = {r.tag_name: r.id for r in rows}

        vault.file_tags.detach(ft_id_by_name[detach_name])

        remaining = tagumori.service.get_file_tag_nodes(vault, [fid])
        assert [r.tag_name for r in remaining] == expected_remaining
