from pathlib import Path

import pytest

from tagumori import crud, service
from tagumori.query import parse, parse_for_storage
from tagumori.query.ast import Expr


def _leaf_paths(conn, file: Path) -> set[tuple[str, ...]]:
    """The resulting leaf paths for a file's tags, for asserting exact tag state."""
    db_file = crud.file.get_by_path(conn, file)
    assert db_file is not None
    rows = crud.file_tag.get_by_file_ids(conn, [db_file.id])
    return service._db_tags_to_leaf_paths(rows)


def _expr(string: str) -> Expr:
    return parse(string)


class TestSearchFiles:
    def test_select_nonexistent_tag_returns_empty(self, conn, make_file):
        """Selecting a tag that no file has should return no files, not all files."""
        file = make_file()

        service.add_tags_to_files(conn, [file], _expr("rock"), apply_tagalongs=False)

        result = service.execute_query(conn, select=_expr("nonexistent"), exclude=None)

        assert result == []

    def test_select_existing_tag_returns_matching_files(self, conn, make_file):
        """Selecting a tag should return only files with that tag."""
        file1 = make_file("rock.txt")
        file2 = make_file("jazz.txt")

        service.add_tags_to_files(conn, [file1], _expr("rock"), apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], _expr("jazz"), apply_tagalongs=False)

        result = service.execute_query(conn, select=_expr("rock"), exclude=None)

        assert len(result) == 1
        assert result[0].path == file1.resolve()

    def test_exclude_only_returns_all_except_excluded(self, conn, make_file):
        """Excluding without selecting should return all files except excluded."""
        file1 = make_file("rock.txt")
        file2 = make_file("jazz.txt")

        service.add_tags_to_files(conn, [file1], _expr("rock"), apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], _expr("jazz"), apply_tagalongs=False)

        result = service.execute_query(conn, select=None, exclude=_expr("rock"))

        assert len(result) == 1
        assert result[0].path == file2.resolve()

    def test_select_case_sensitive_by_default(self, conn, make_file):
        """Tag search is case-sensitive by default."""
        file = make_file()

        service.add_tags_to_files(conn, [file], _expr("Rock"), apply_tagalongs=False)

        result = service.execute_query(conn, select=_expr("rock"), exclude=None)

        assert result == []

    def test_select_ignore_tag_case(self, conn, make_file):
        """With ignore_tag_case, tag search should be case-insensitive."""
        file = make_file()

        service.add_tags_to_files(conn, [file], _expr("Rock"), apply_tagalongs=False)

        result = service.execute_query(
            conn, select=_expr("rock"), exclude=None, ignore_tag_case=True
        )

        assert len(result) == 1
        assert result[0].path == file.resolve()


class TestSetTagsOnFiles:
    """`set` must replace a file's tags with exactly the given expression,
    in a single call, regardless of how deep the unwanted branch is.
    """

    @pytest.mark.parametrize(
        "initial, set_to, expected",
        [
            pytest.param(
                "a[b[c]]",
                "b",
                {("b",)},
                id="collapses-multi-level-unwanted-branch-in-one-call",
            ),
            pytest.param(
                "a[b],a[c]",
                "a[b]",
                {("a", "b")},
                id="partial-branch-removal-still-works",
            ),
            pytest.param(
                "a[b[c]]",
                "a[b]",
                {("a", "b")},
                id="shortens-a-branch-by-one-level",
            ),
            pytest.param(
                "a,b",
                "a",
                {("a",)},
                id="drops-a-whole-sibling-tag",
            ),
            pytest.param(
                "a[b[c]]",
                "a[b[c]]",
                {("a", "b", "c")},
                id="setting-to-the-same-tags-is-a-no-op",
            ),
            pytest.param(
                "x[y]",
                "p[q]",
                {("p", "q")},
                id="total-replacement-with-disjoint-tags",
            ),
            pytest.param(
                "a[b]",
                "a",
                {("a",)},
                id="removes-a-leaf-promoting-its-parent",
            ),
        ],
    )
    def test_set_tags(self, conn, make_file, initial, set_to, expected):
        file = make_file()

        service.add_tags_to_files(conn, [file], _expr(initial), apply_tagalongs=False)
        service.set_tags_on_files(conn, [file], _expr(set_to), apply_tagalongs=False)

        assert _leaf_paths(conn, file) == expected

    def test_applies_the_same_result_to_every_file(self, conn, make_file):
        """set on multiple files with different starting tags converges both
        to exactly the same result."""
        file1 = make_file("file1.txt")
        file2 = make_file("file2.txt")

        service.add_tags_to_files(
            conn, [file1], _expr("a[b[c]]"), apply_tagalongs=False
        )
        service.add_tags_to_files(conn, [file2], _expr("q"), apply_tagalongs=False)

        service.set_tags_on_files(
            conn, [file1, file2], _expr("x[a]"), apply_tagalongs=False
        )

        assert _leaf_paths(conn, file1) == {("x", "a")}
        assert _leaf_paths(conn, file2) == {("x", "a")}


class TestRemoveTagsFromFiles:
    @pytest.mark.parametrize(
        "initial, remove, expected",
        [
            pytest.param(
                "a[b[c]]",
                "a",
                set(),
                id="removing-a-node-cascades-its-whole-subtree",
            ),
            pytest.param(
                "a[b,c]",
                "a[b]",
                {("a", "c")},
                id="removing-one-branch-keeps-its-siblings",
            ),
            pytest.param(
                "a[b]",
                "zzz",
                {("a", "b")},
                id="removing-a-nonexistent-tag-is-a-no-op",
            ),
        ],
    )
    def test_remove_tags(self, conn, make_file, initial, remove, expected):
        file = make_file()

        service.add_tags_to_files(conn, [file], _expr(initial), apply_tagalongs=False)
        service.remove_tags_from_files(conn, [file], _expr(remove))

        assert _leaf_paths(conn, file) == expected

    def test_applies_to_every_file_independently(self, conn, make_file):
        """Two files sharing a branch: removing it should leave each file's
        own remaining tags intact."""
        file1 = make_file("file1.txt")
        file2 = make_file("file2.txt")

        service.add_tags_to_files(conn, [file1], _expr("x[a],y"), apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], _expr("x[a],z"), apply_tagalongs=False)

        service.remove_tags_from_files(conn, [file1, file2], _expr("x[a]"))

        assert _leaf_paths(conn, file1) == {("x",), ("y",)}
        assert _leaf_paths(conn, file2) == {("x",), ("z",)}


class TestAstToPaths:
    """Root-to-leaf paths only - interior nodes don't get their own entry."""

    @pytest.mark.parametrize(
        "tags, expected",
        [
            pytest.param("a", {("a",)}, id="single-tag"),
            pytest.param(
                "a[b[c]]", {("a", "b", "c")}, id="linear-chain-only-yields-the-leaf"
            ),
            pytest.param(
                "a[b[c],d]",
                {("a", "b", "c"), ("a", "d")},
                id="branching-tree-yields-one-path-per-leaf",
            ),
        ],
    )
    def test_ast_to_leaf_paths(self, tags, expected):
        node = parse_for_storage(tags)
        assert service._ast_to_leaf_paths(node) == expected


class TestAstToClosure:
    """Downward closure of the leaf paths under the prefix order: every leaf
    path, plus every prefix of it - i.e. a materialized path for every node,
    not just leaves.
    """

    @pytest.mark.parametrize(
        "tags, expected",
        [
            pytest.param("a", {("a",)}, id="single-tag"),
            pytest.param(
                "a[b[c]]",
                {("a",), ("a", "b"), ("a", "b", "c")},
                id="linear-chain-includes-every-ancestor",
            ),
            pytest.param(
                "a[b[c],d]",
                {("a",), ("a", "b"), ("a", "b", "c"), ("a", "d")},
                id="branching-tree-is-flattened",
            ),
            pytest.param(
                "a,b",
                {("a",), ("b",)},
                id="top-level-and-is-flattened",
            ),
        ],
    )
    def test_ast_to_path_closure(self, tags, expected):
        """The `branching-tree-is-flattened` and `top-level-and-is-flattened`
        cases are regressions: an And nested under a Tag, or at the top
        level, used to come back as a nested list instead of a flat set.
        """
        node = parse_for_storage(tags)
        assert service._ast_to_path_closure(node) == expected


class TestPathsById:
    """Materialized path for every existing file_tag row, not just leaves."""

    def test_linear_chain(self, conn, make_file):
        file = make_file()
        service.add_tags_to_files(conn, [file], _expr("a[b[c]]"), apply_tagalongs=False)

        db_file = crud.file.get_by_path(conn, file)
        assert db_file is not None
        rows = crud.file_tag.get_by_file_ids(conn, [db_file.id])

        assert set(service._paths_by_id(rows).values()) == {
            ("a",),
            ("a", "b"),
            ("a", "b", "c"),
        }

    def test_branching_tree(self, conn, make_file):
        file = make_file()
        service.add_tags_to_files(conn, [file], _expr("a[b,c]"), apply_tagalongs=False)

        db_file = crud.file.get_by_path(conn, file)
        assert db_file is not None
        rows = crud.file_tag.get_by_file_ids(conn, [db_file.id])

        assert set(service._paths_by_id(rows).values()) == {
            ("a",),
            ("a", "b"),
            ("a", "c"),
        }

    def test_multiple_files_produce_independent_trees(self, conn, make_file):
        """Rows pooled from more than one file must not have their paths
        cross-linked, since set/remove fetch all files' rows in one call."""
        file1 = make_file("file1.txt")
        file2 = make_file("file2.txt")
        service.add_tags_to_files(conn, [file1], _expr("a[b]"), apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], _expr("a[c]"), apply_tagalongs=False)

        db_files = [crud.file.get_by_path(conn, f) for f in (file1, file2)]
        ids = [f.id for f in db_files if f is not None]
        rows = crud.file_tag.get_by_file_ids(conn, ids)

        assert set(service._paths_by_id(rows).values()) == {
            ("a",),
            ("a", "b"),
            ("a", "c"),
        }
