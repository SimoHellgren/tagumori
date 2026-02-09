from pathlib import Path

from filetags import crud
from filetags.query import search
from filetags.query.executor import execute, find_all
from filetags.query.planner import (
    QP_And,
    QP_Not,
    QP_OnlyOne,
    QP_Or,
    QP_Xor,
    SegmentTag,
    SegmentWildCardSingle,
    TagPath,
)


def make_file(conn, path_str, tag_paths):
    """Creates a file and attaches tag trees.

    tag_paths is a list of tuples, e.g. [("genre", "rock"), ("mood",)]
    Each tuple is a root -> child -> grandchild chain.
    """
    file_row = crud.file.get_or_create(conn, Path(path_str))
    for tag_path in tag_paths:
        parent_id = None
        for tag_name in tag_path:
            tag = crud.tag.get_or_create(conn, tag_name)
            parent_id = crud.file_tag.attach(conn, file_row["id"], tag["id"], parent_id)
    return file_row["id"]


class TestFindAllSimple:
    def test_single_tag_match(self, conn):
        fid = make_file(conn, "song.mp3", [("rock",)])
        assert find_all(conn, [SegmentTag("rock")], True) == {fid}

    def test_single_tag_no_match(self, conn):
        make_file(conn, "song.mp3", [("rock",)])
        assert find_all(conn, [SegmentTag("jazz")], True) == set()

    def test_path_two_segments(self, conn):
        fid = make_file(conn, "song.mp3", [("genre", "rock")])
        assert find_all(conn, [SegmentTag("genre"), SegmentTag("rock")], True) == {fid}

    def test_path_partial_match_fails(self, conn):
        make_file(conn, "song.mp3", [("genre", "rock")])
        assert find_all(conn, [SegmentTag("genre"), SegmentTag("jazz")], True) == set()

    def test_multiple_files_returns_matching(self, conn):
        fid1 = make_file(conn, "a.mp3", [("rock",)])
        make_file(conn, "b.mp3", [("jazz",)])
        assert find_all(conn, [SegmentTag("rock")], True) == {fid1}


class TestFindAllWildcard:
    def test_wildcard_single_matches_any_tag(self, conn):
        fid = make_file(conn, "song.mp3", [("rock",)])
        assert find_all(conn, [SegmentWildCardSingle()], True) == {fid}

    def test_wildcard_single_in_path(self, conn):
        fid = make_file(conn, "song.mp3", [("genre", "rock")])
        result = find_all(conn, [SegmentTag("genre"), SegmentWildCardSingle()], True)
        assert result == {fid}

    def test_wildcard_at_prefix_position(self, conn):
        fid = make_file(conn, "song.mp3", [("genre", "rock")])
        result = find_all(conn, [SegmentWildCardSingle(), SegmentTag("rock")], True)
        assert result == {fid}


class TestFindAllRootAndLeaf:
    def test_is_root_matches_root_tag(self, conn):
        fid = make_file(conn, "song.mp3", [("rock",)])
        assert find_all(conn, [SegmentTag("rock", is_root=True)], True) == {fid}

    def test_is_root_excludes_non_root(self, conn):
        make_file(conn, "song.mp3", [("genre", "rock")])
        # rock is a child of genre, not a root
        assert find_all(conn, [SegmentTag("rock", is_root=True)], True) == set()

    def test_is_leaf_matches_leaf_tag(self, conn):
        fid = make_file(conn, "song.mp3", [("genre", "rock")])
        # rock is a leaf (no children)
        result = find_all(
            conn, [SegmentTag("genre"), SegmentTag("rock", is_leaf=True)], True
        )
        assert result == {fid}

    def test_is_leaf_excludes_non_leaf(self, conn):
        make_file(conn, "song.mp3", [("genre", "rock")])
        # genre has children, so is_leaf should exclude it
        assert find_all(conn, [SegmentTag("genre", is_leaf=True)], True) == set()

    def test_root_and_leaf_combined(self, conn):
        # ~ matches root-level tags with no children
        fid1 = make_file(conn, "a.mp3", [("rock",)])  # root + leaf
        make_file(conn, "b.mp3", [("genre", "rock")])  # genre is root but not leaf
        result = find_all(
            conn, [SegmentWildCardSingle(is_root=True, is_leaf=True)], True
        )
        assert result == {fid1}


class TestFindAllCaseInsensitive:
    def test_case_sensitive_no_match(self, conn):
        make_file(conn, "song.mp3", [("Rock",)])
        assert find_all(conn, [SegmentTag("rock")], True) == set()

    def test_case_insensitive_matches(self, conn):
        fid = make_file(conn, "song.mp3", [("Rock",)])
        assert find_all(conn, [SegmentTag("rock")], False) == {fid}


class TestExecuteOperators:
    def setup_method(self):
        """Store expected ids for use in tests. Actual setup in each test via conn."""
        pass

    def _setup_three_files(self, conn):
        f1 = make_file(conn, "a.mp3", [("rock",)])
        f2 = make_file(conn, "b.mp3", [("jazz",)])
        f3 = make_file(conn, "c.mp3", [("rock",), ("jazz",)])
        return f1, f2, f3

    def test_and_intersection(self, conn):
        f1, f2, f3 = self._setup_three_files(conn)
        qp = QP_And([TagPath([SegmentTag("rock")]), TagPath([SegmentTag("jazz")])])
        assert execute(conn, qp) == {f3}

    def test_or_union(self, conn):
        f1, f2, f3 = self._setup_three_files(conn)
        qp = QP_Or([TagPath([SegmentTag("rock")]), TagPath([SegmentTag("jazz")])])
        assert execute(conn, qp) == {f1, f2, f3}

    def test_not_complement(self, conn):
        f1, f2, f3 = self._setup_three_files(conn)
        qp = QP_Not(TagPath([SegmentTag("rock")]))
        assert execute(conn, qp) == {f2}

    def test_xor_symmetric_difference(self, conn):
        f1, f2, f3 = self._setup_three_files(conn)
        qp = QP_Xor([TagPath([SegmentTag("rock")]), TagPath([SegmentTag("jazz")])])
        assert execute(conn, qp) == {f1, f2}

    def test_only_one(self, conn):
        f1, f2, f3 = self._setup_three_files(conn)
        qp = QP_OnlyOne([TagPath([SegmentTag("rock")]), TagPath([SegmentTag("jazz")])])
        assert execute(conn, qp) == {f1, f2}

    def test_and_empty_operand(self, conn):
        self._setup_three_files(conn)
        qp = QP_And(
            [TagPath([SegmentTag("nonexistent")]), TagPath([SegmentTag("rock")])]
        )
        assert execute(conn, qp) == set()


class TestExecuteOnlyOneVsXor:
    def test_three_operands_all_match_diverges(self, conn):
        """With 3 operands all matching the same file:
        - XOR: odd parity (3 is odd) -> file IS included
        - OnlyOne: count=3 -> file is EXCLUDED
        """
        fid = make_file(conn, "song.mp3", [("a",), ("b",), ("c",)])

        rock = TagPath([SegmentTag("a")])
        jazz = TagPath([SegmentTag("b")])
        blues = TagPath([SegmentTag("c")])

        xor_result = execute(conn, QP_Xor([rock, jazz, blues]))
        only_one_result = execute(conn, QP_OnlyOne([rock, jazz, blues]))

        assert fid in xor_result
        assert fid not in only_one_result

    def test_three_operands_one_match_agrees(self, conn):
        """With only 1 operand matching: both XOR and OnlyOne include the file."""
        fid = make_file(conn, "song.mp3", [("a",)])

        rock = TagPath([SegmentTag("a")])
        jazz = TagPath([SegmentTag("b")])
        blues = TagPath([SegmentTag("c")])

        xor_result = execute(conn, QP_Xor([rock, jazz, blues]))
        only_one_result = execute(conn, QP_OnlyOne([rock, jazz, blues]))

        assert fid in xor_result
        assert fid in only_one_result


class TestSearchEndToEnd:
    def test_simple_tag(self, conn):
        fid = make_file(conn, "song.mp3", [("rock",)])
        assert search(conn, "rock") == {fid}

    def test_hierarchical_query(self, conn):
        fid = make_file(conn, "song.mp3", [("genre", "rock")])
        assert search(conn, "genre[rock]") == {fid}

    def test_and_query(self, conn):
        make_file(conn, "a.mp3", [("rock",)])
        make_file(conn, "b.mp3", [("jazz",)])
        f3 = make_file(conn, "c.mp3", [("rock",), ("jazz",)])
        assert search(conn, "rock,jazz") == {f3}

    def test_or_query(self, conn):
        f1 = make_file(conn, "a.mp3", [("rock",)])
        f2 = make_file(conn, "b.mp3", [("jazz",)])
        assert search(conn, "rock|jazz") == {f1, f2}

    def test_not_query(self, conn):
        make_file(conn, "a.mp3", [("rock",)])
        f2 = make_file(conn, "b.mp3", [("jazz",)])
        assert search(conn, "!rock") == {f2}

    def test_not_inside_brackets(self, conn):
        make_file(conn, "a.mp3", [("genre", "rock")])
        f2 = make_file(conn, "b.mp3", [("genre", "jazz")])
        # genre[!rock]: files with genre but NOT genre->rock
        assert search(conn, "genre[!rock]") == {f2}

    def test_null_bare_matches_root_leaves(self, conn):
        f1 = make_file(conn, "a.mp3", [("rock",)])  # root + leaf
        make_file(conn, "b.mp3", [("genre", "rock")])  # genre is root but not leaf
        assert search(conn, "~") == {f1}

    def test_null_with_child_root_constraint(self, conn):
        f1 = make_file(conn, "a.mp3", [("rock",)])  # rock is root
        make_file(conn, "b.mp3", [("genre", "rock")])  # rock is NOT root
        assert search(conn, "~[rock]") == {f1}

    def test_wildcard_single_with_child(self, conn):
        fid = make_file(conn, "song.mp3", [("genre", "rock")])
        # *[rock]: any tag that has child "rock"
        assert search(conn, "*[rock]") == {fid}

    def test_case_insensitive(self, conn):
        fid = make_file(conn, "song.mp3", [("Rock",)])
        assert search(conn, "rock", case=False) == {fid}
