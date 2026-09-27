import pytest

from tagumori.query import parse, parse_for_storage
from tagumori.query.ast import (
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


class TestParseSingleTag:
    def test_simple_name(self):
        assert parse("rock") == Tag("rock")

    def test_name_with_spaces(self):
        assert parse("Will Smith") == Tag("Will Smith")

    def test_unicode_name(self):
        assert parse("日本語") == Tag("日本語")

    def test_name_with_hyphens_and_underscores(self):
        assert parse("foo-bar_baz") == Tag("foo-bar_baz")

    def test_xor_as_tag_name(self):
        assert parse("xor") == Tag("xor")

    def test_leading_trailing_whitespace_trimmed(self):
        assert parse("  rock  ") == Tag("rock")


class TestParseBrackets:
    def test_tag_with_child(self):
        assert parse("genre[rock]") == Tag("genre", Tag("rock"))

    def test_nested_two_levels(self):
        assert parse("a[b[c]]") == Tag("a", Tag("b", Tag("c")))

    def test_bracket_with_and(self):
        assert parse("genre[rock,jazz]") == Tag(
            "genre", And([Tag("rock"), Tag("jazz")])
        )

    def test_bracket_with_or(self):
        assert parse("genre[rock|jazz]") == Tag("genre", Or([Tag("rock"), Tag("jazz")]))

    def test_bracket_with_not(self):
        assert parse("a[!b]") == Tag("a", Not(Tag("b")))


class TestParseOperators:
    def test_and(self):
        assert parse("a,b") == And([Tag("a"), Tag("b")])

    def test_or(self):
        assert parse("a|b") == Or([Tag("a"), Tag("b")])

    def test_xor(self):
        assert parse("a^b") == Xor([Tag("a"), Tag("b")])

    def test_not(self):
        assert parse("!a") == Not(Tag("a"))

    def test_only_one_two_args(self):
        assert parse("xor(a,b)") == OnlyOne([Tag("a"), Tag("b")])

    def test_only_one_three_args(self):
        assert parse("xor(a,b,c)") == OnlyOne([Tag("a"), Tag("b"), Tag("c")])


class TestParsePrecedence:
    def test_not_binds_tighter_than_and(self):
        # !a,b -> AND(NOT(a), b)
        assert parse("!a,b") == And([Not(Tag("a")), Tag("b")])

    def test_and_binds_tighter_than_or(self):
        # a,b|c -> OR(AND(a,b), c)
        assert parse("a,b|c") == Or([And([Tag("a"), Tag("b")]), Tag("c")])

    def test_or_binds_tighter_than_xor(self):
        # a|b^c -> XOR(OR(a,b), c)
        assert parse("a|b^c") == Xor([Or([Tag("a"), Tag("b")]), Tag("c")])

    def test_parens_override_precedence(self):
        # a,(b|c) -> AND(a, OR(b,c))
        assert parse("a,(b|c)") == And([Tag("a"), Or([Tag("b"), Tag("c")])])

    def test_double_negation_preserved(self):
        assert parse("!!a") == Not(Not(Tag("a")))


class TestParseWildcards:
    def test_null_bare(self):
        assert parse("~") == Null()

    def test_null_with_child(self):
        assert parse("~[a]") == Null(Tag("a"))

    def test_wildcard_single_bare(self):
        assert parse("*") == WildcardSingle()

    def test_wildcard_single_with_child(self):
        assert parse("*[a]") == WildcardSingle(Tag("a"))

    def test_wildcard_path(self):
        assert parse("**") == WildcardPath()

    def test_wildcard_bounded(self):
        assert parse("*3*") == WildcardBounded(3)


class TestParseForStorage:
    def test_single_tag_valid(self):
        assert parse_for_storage("rock") == Tag("rock")

    def test_and_valid(self):
        assert parse_for_storage("a,b") == And([Tag("a"), Tag("b")])

    def test_nested_tag_valid(self):
        assert parse_for_storage("a[b]") == Tag("a", Tag("b"))

    @pytest.mark.parametrize(
        "expr",
        ["a|b", "!a", "*", "~"],
        ids=["or", "not", "wildcard", "null"],
    )
    def test_rejected(self, expr):
        with pytest.raises(ValueError):
            parse_for_storage(expr)


class TestAstStr:
    @pytest.mark.parametrize(
        "ast, expected_str",
        [
            pytest.param(Tag("a"), "a", id="simple"),
            pytest.param(Tag("a", Tag("b")), "a[b]", id="nested"),
            pytest.param(And([Tag("a"), Tag("b")]), "a,b", id="and"),
            pytest.param(Or([Tag("a"), Tag("b")]), "a|b", id="or"),
            pytest.param(Not(Tag("a")), "!a", id="not"),
            pytest.param(OnlyOne([Tag("a"), Tag("b")]), "xor(a,b)", id="only_one"),
        ],
    )
    def test_roundtrip(self, ast, expected_str):
        assert str(ast) == expected_str
        assert parse(str(ast)) == ast
