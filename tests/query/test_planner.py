import pytest

from filetags.query.ast import (
    And,
    Not,
    Null,
    OnlyOne,
    Or,
    Tag,
    WildcardBounded,
    WildcardPath,
    WildcardSingle,
    Xor,
)
from filetags.query.planner import (
    QP_And,
    QP_Not,
    QP_OnlyOne,
    QP_Or,
    QP_Xor,
    SegmentTag,
    SegmentWildCardSingle,
    TagPath,
    simplify,
    to_query_plan,
)


class TestToQueryPlanBasic:
    def test_simple_tag(self):
        assert to_query_plan(Tag("a")) == TagPath([SegmentTag("a")])

    def test_nested_tag(self):
        assert to_query_plan(Tag("a", Tag("b"))) == TagPath(
            [SegmentTag("a"), SegmentTag("b")]
        )

    def test_three_level_tag(self):
        assert to_query_plan(Tag("a", Tag("b", Tag("c")))) == TagPath(
            [SegmentTag("a"), SegmentTag("b"), SegmentTag("c")]
        )

    def test_wildcard_single_bare(self):
        assert to_query_plan(WildcardSingle()) == TagPath([SegmentWildCardSingle()])

    def test_wildcard_single_with_child(self):
        assert to_query_plan(WildcardSingle(Tag("a"))) == TagPath(
            [SegmentWildCardSingle(), SegmentTag("a")]
        )


class TestToQueryPlanNull:
    def test_null_bare_is_root_leaf_wildcard(self):
        # ~ alone: any root-level tag with no children
        assert to_query_plan(Null()) == TagPath(
            [SegmentWildCardSingle(is_root=True, is_leaf=True)]
        )

    def test_null_with_child_propagates_is_root(self):
        # ~[a]: a must be a root
        assert to_query_plan(Null(Tag("a"))) == TagPath(
            [SegmentTag("a", is_root=True)]
        )

    def test_tag_with_null_child_sets_is_leaf(self):
        # a[~]: a must be a leaf
        assert to_query_plan(Tag("a", Null())) == TagPath(
            [SegmentTag("a", is_leaf=True)]
        )

    def test_null_nested_stops_recursion(self):
        # a[~[z]] truncates to a[~], the z is silently dropped
        assert to_query_plan(Tag("a", Null(Tag("z")))) == TagPath(
            [SegmentTag("a", is_leaf=True)]
        )


class TestToQueryPlanOperators:
    def test_and(self):
        result = to_query_plan(And([Tag("a"), Tag("b")]))
        assert result == QP_And(
            [TagPath([SegmentTag("a")]), TagPath([SegmentTag("b")])]
        )

    def test_or(self):
        result = to_query_plan(Or([Tag("a"), Tag("b")]))
        assert result == QP_Or(
            [TagPath([SegmentTag("a")]), TagPath([SegmentTag("b")])]
        )

    def test_xor(self):
        result = to_query_plan(Xor([Tag("a"), Tag("b")]))
        assert result == QP_Xor(
            [TagPath([SegmentTag("a")]), TagPath([SegmentTag("b")])]
        )

    def test_only_one(self):
        result = to_query_plan(OnlyOne([Tag("a"), Tag("b")]))
        assert result == QP_OnlyOne(
            [TagPath([SegmentTag("a")]), TagPath([SegmentTag("b")])]
        )

    def test_not_at_top_level(self):
        result = to_query_plan(Not(Tag("a")))
        assert result == QP_Not(TagPath([SegmentTag("a")]))


class TestToQueryPlanNotInBrackets:
    def test_not_inside_bracket(self):
        # a[!b] -> QP_And([TagPath(a), QP_Not(TagPath(a, b))])
        result = to_query_plan(Tag("a", Not(Tag("b"))))
        assert result == QP_And(
            [
                TagPath([SegmentTag("a")]),
                QP_Not(TagPath([SegmentTag("a"), SegmentTag("b")])),
            ]
        )

    def test_not_at_top_level_no_prefix_duplication(self):
        # !a -> QP_Not(TagPath(a)), no wrapping QP_And
        result = to_query_plan(Not(Tag("a")))
        assert result == QP_Not(TagPath([SegmentTag("a")]))

    def test_not_deep_nested(self):
        # x[y[!z]] -> QP_And([TagPath(x, y), QP_Not(TagPath(x, y, z))])
        result = to_query_plan(Tag("x", Tag("y", Not(Tag("z")))))
        assert result == QP_And(
            [
                TagPath([SegmentTag("x"), SegmentTag("y")]),
                QP_Not(TagPath([SegmentTag("x"), SegmentTag("y"), SegmentTag("z")])),
            ]
        )


class TestToQueryPlanNotImplemented:
    def test_wildcard_path_raises(self):
        with pytest.raises(NotImplementedError):
            to_query_plan(WildcardPath())

    def test_wildcard_bounded_raises(self):
        with pytest.raises(NotImplementedError):
            to_query_plan(WildcardBounded(3))


# helpers for simplify tests
a = TagPath([SegmentTag("a")])
b = TagPath([SegmentTag("b")])
c = TagPath([SegmentTag("c")])
d = TagPath([SegmentTag("d")])


class TestSimplify:
    def test_tagpath_unchanged(self):
        assert simplify(a) == a

    def test_flatten_nested_and(self):
        assert simplify(QP_And([QP_And([a, b]), c])) == QP_And([a, b, c])

    def test_flatten_nested_or(self):
        assert simplify(QP_Or([QP_Or([a, b]), c])) == QP_Or([a, b, c])

    def test_unwrap_single_and(self):
        assert simplify(QP_And([a])) == a

    def test_unwrap_single_or(self):
        assert simplify(QP_Or([a])) == a

    def test_unwrap_single_xor(self):
        assert simplify(QP_Xor([a])) == a

    def test_unwrap_single_only_one(self):
        assert simplify(QP_OnlyOne([a])) == a

    def test_double_negation(self):
        assert simplify(QP_Not(QP_Not(a))) == a

    def test_triple_negation(self):
        assert simplify(QP_Not(QP_Not(QP_Not(a)))) == QP_Not(a)

    def test_deep_flatten(self):
        assert simplify(QP_And([QP_And([QP_And([a, b]), c]), d])) == QP_And(
            [a, b, c, d]
        )

    def test_no_cross_type_flatten(self):
        # OR inside AND should not be flattened
        result = simplify(QP_And([QP_Or([a, b]), c]))
        assert result == QP_And([QP_Or([a, b]), c])
