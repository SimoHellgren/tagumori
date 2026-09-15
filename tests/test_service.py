from pathlib import Path

from tagumori import crud, service
from tagumori.query import parse_for_storage


def _leaf_paths(conn, file: Path) -> set[tuple[str, ...]]:
    """The resulting leaf paths for a file's tags, for asserting exact tag state."""
    db_file = crud.file.get_by_path(conn, file)
    assert db_file is not None
    rows = crud.file_tag.get_by_file_ids(conn, [db_file.id])
    return service._db_tags_to_leaf_paths(rows)


class TestSearchFiles:
    def test_select_nonexistent_tag_returns_empty(self, conn, tmp_path):
        """Selecting a tag that no file has should return no files, not all files."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["rock"], apply_tagalongs=False)

        result = service.execute_query(
            conn, select_strs=["nonexistent"], exclude_strs=[]
        )

        assert result == []

    def test_select_existing_tag_returns_matching_files(self, conn, tmp_path):
        """Selecting a tag should return only files with that tag."""
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], ["rock"], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], ["jazz"], apply_tagalongs=False)

        result = service.execute_query(conn, select_strs=["rock"], exclude_strs=[])

        assert len(result) == 1
        assert result[0].path == file1.resolve()

    def test_exclude_only_returns_all_except_excluded(self, conn, tmp_path):
        """Excluding without selecting should return all files except excluded."""
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], ["rock"], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], ["jazz"], apply_tagalongs=False)

        result = service.execute_query(conn, select_strs=[], exclude_strs=["rock"])

        assert len(result) == 1
        assert result[0].path == file2.resolve()

    def test_select_case_sensitive_by_default(self, conn, tmp_path):
        """Tag search is case-sensitive by default."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["Rock"], apply_tagalongs=False)

        result = service.execute_query(conn, select_strs=["rock"], exclude_strs=[])

        assert result == []

    def test_select_ignore_tag_case(self, conn, tmp_path):
        """With ignore_tag_case, tag search should be case-insensitive."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["Rock"], apply_tagalongs=False)

        result = service.execute_query(
            conn, select_strs=["rock"], exclude_strs=[], ignore_tag_case=True
        )

        assert len(result) == 1
        assert result[0].path == file.resolve()


class TestSetTagsOnFiles:
    """`set` must replace a file's tags with exactly the given expression,
    in a single call, regardless of how deep the unwanted branch is.
    """

    def test_collapses_a_multi_level_unwanted_branch_in_one_call(self, conn, tmp_path):
        """The original bug: a[b[c]] -> set b used to take 3 calls to converge."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b[c]]"], apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], ["b"], apply_tagalongs=False)

        assert _leaf_paths(conn, file) == {("b",)}

    def test_partial_branch_removal_still_works(self, conn, tmp_path):
        """a[b],a[c] -> set a[b]: the case that already worked before the fix."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b],a[c]"], apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], ["a[b]"], apply_tagalongs=False)

        assert _leaf_paths(conn, file) == {("a", "b")}

    def test_shortens_a_branch_by_one_level(self, conn, tmp_path):
        """a[b[c]] -> set a[b]."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b[c]]"], apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], ["a[b]"], apply_tagalongs=False)

        assert _leaf_paths(conn, file) == {("a", "b")}

    def test_drops_a_whole_sibling_tag(self, conn, tmp_path):
        """a,b -> set a."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a,b"], apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], ["a"], apply_tagalongs=False)

        assert _leaf_paths(conn, file) == {("a",)}

    def test_setting_to_the_same_tags_is_a_no_op(self, conn, tmp_path):
        """Identity case: set to the tags a file already has."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b[c]]"], apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], ["a[b[c]]"], apply_tagalongs=False)

        assert _leaf_paths(conn, file) == {("a", "b", "c")}

    def test_total_replacement_with_disjoint_tags(self, conn, tmp_path):
        """x[y] -> set p[q]: nothing in the new tree overlaps the old one."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["x[y]"], apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], ["p[q]"], apply_tagalongs=False)

        assert _leaf_paths(conn, file) == {("p", "q")}

    def test_removes_a_leaf_promoting_its_parent(self, conn, tmp_path):
        """a[b] -> set a."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b]"], apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], ["a"], apply_tagalongs=False)

        assert _leaf_paths(conn, file) == {("a",)}

    def test_applies_the_same_result_to_every_file(self, conn, tmp_path):
        """set on multiple files with different starting tags converges both
        to exactly the same result."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], ["a[b[c]]"], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], ["q"], apply_tagalongs=False)

        service.set_tags_on_files(conn, [file1, file2], ["x[a]"], apply_tagalongs=False)

        assert _leaf_paths(conn, file1) == {("x", "a")}
        assert _leaf_paths(conn, file2) == {("x", "a")}


class TestRemoveTagsFromFiles:
    def test_removing_a_node_cascades_its_whole_subtree(self, conn, tmp_path):
        """remove -t a on a[b[c]] should drop a, b, and c together."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b[c]]"], apply_tagalongs=False)
        service.remove_tags_from_files(conn, [file], ["a"])

        assert _leaf_paths(conn, file) == set()

    def test_removing_one_branch_keeps_its_siblings(self, conn, tmp_path):
        """a[b,c] -> remove a[b] should leave a[c] untouched."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b,c]"], apply_tagalongs=False)
        service.remove_tags_from_files(conn, [file], ["a[b]"])

        assert _leaf_paths(conn, file) == {("a", "c")}

    def test_removing_a_nonexistent_tag_is_a_no_op(self, conn, tmp_path):
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["a[b]"], apply_tagalongs=False)
        service.remove_tags_from_files(conn, [file], ["zzz"])

        assert _leaf_paths(conn, file) == {("a", "b")}

    def test_applies_to_every_file_independently(self, conn, tmp_path):
        """Two files sharing a branch: removing it should leave each file's
        own remaining tags intact."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], ["x[a],y"], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], ["x[a],z"], apply_tagalongs=False)

        service.remove_tags_from_files(conn, [file1, file2], ["x[a]"])

        assert _leaf_paths(conn, file1) == {("x",), ("y",)}
        assert _leaf_paths(conn, file2) == {("x",), ("z",)}


class TestAstToPaths:
    """Root-to-leaf paths only - interior nodes don't get their own entry."""

    def test_single_tag(self):
        node = parse_for_storage("a")
        assert service._ast_to_leaf_paths(node) == {("a",)}

    def test_linear_chain_only_yields_the_leaf(self):
        node = parse_for_storage("a[b[c]]")
        assert service._ast_to_leaf_paths(node) == {("a", "b", "c")}

    def test_branching_tree_yields_one_path_per_leaf(self):
        node = parse_for_storage("a[b[c],d]")
        assert service._ast_to_leaf_paths(node) == {("a", "b", "c"), ("a", "d")}


class TestAstToClosure:
    """Downward closure of the leaf paths under the prefix order: every leaf
    path, plus every prefix of it - i.e. a materialized path for every node,
    not just leaves.
    """

    def test_single_tag(self):
        node = parse_for_storage("a")
        assert service._ast_to_path_closure(node) == {("a",)}

    def test_linear_chain_includes_every_ancestor(self):
        node = parse_for_storage("a[b[c]]")
        assert service._ast_to_path_closure(node) == {("a",), ("a", "b"), ("a", "b", "c")}

    def test_branching_tree_is_flattened(self):
        """Regression: an And nested under a Tag used to come back as a
        nested list instead of a flat set."""
        node = parse_for_storage("a[b[c],d]")
        assert service._ast_to_path_closure(node) == {
            ("a",),
            ("a", "b"),
            ("a", "b", "c"),
            ("a", "d"),
        }

    def test_top_level_and_is_flattened(self):
        """Regression: a top-level And (e.g. 'a,b') used to come back as a
        list of one-element lists instead of a flat set."""
        node = parse_for_storage("a,b")
        assert service._ast_to_path_closure(node) == {("a",), ("b",)}


class TestPathsById:
    """Materialized path for every existing file_tag row, not just leaves."""

    def test_linear_chain(self, conn, tmp_path):
        file = tmp_path / "file.txt"
        file.write_text("")
        service.add_tags_to_files(conn, [file], ["a[b[c]]"], apply_tagalongs=False)

        db_file = crud.file.get_by_path(conn, file)
        assert db_file is not None
        rows = crud.file_tag.get_by_file_ids(conn, [db_file.id])

        assert set(service._paths_by_id(rows).values()) == {
            ("a",),
            ("a", "b"),
            ("a", "b", "c"),
        }

    def test_branching_tree(self, conn, tmp_path):
        file = tmp_path / "file.txt"
        file.write_text("")
        service.add_tags_to_files(conn, [file], ["a[b,c]"], apply_tagalongs=False)

        db_file = crud.file.get_by_path(conn, file)
        assert db_file is not None
        rows = crud.file_tag.get_by_file_ids(conn, [db_file.id])

        assert set(service._paths_by_id(rows).values()) == {
            ("a",),
            ("a", "b"),
            ("a", "c"),
        }

    def test_multiple_files_produce_independent_trees(self, conn, tmp_path):
        """Rows pooled from more than one file must not have their paths
        cross-linked, since set/remove fetch all files' rows in one call."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("")
        file2.write_text("")
        service.add_tags_to_files(conn, [file1], ["a[b]"], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], ["a[c]"], apply_tagalongs=False)

        db_files = [crud.file.get_by_path(conn, f) for f in (file1, file2)]
        ids = [f.id for f in db_files if f is not None]
        rows = crud.file_tag.get_by_file_ids(conn, ids)

        assert set(service._paths_by_id(rows).values()) == {
            ("a",),
            ("a", "b"),
            ("a", "c"),
        }
