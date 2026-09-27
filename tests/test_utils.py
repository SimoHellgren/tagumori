import pytest

from tagumori.utils import compile_matcher


@pytest.mark.parametrize("invert_match", [False, True])
@pytest.mark.parametrize("ignore_case", [False, True])
class TestCompileMatcher:
    def test_basic_match(self, ignore_case, invert_match):
        matcher = compile_matcher("foo", ignore_case, invert_match)

        assert matcher("foo") == (True ^ invert_match)
        assert matcher("foobar") == (True ^ invert_match)
        assert matcher("bar") == (False ^ invert_match)

    def test_case_sensitivity(self, ignore_case, invert_match):
        matcher = compile_matcher("foo", ignore_case, invert_match)

        assert matcher("FOO") == (ignore_case ^ invert_match)
        assert matcher("Foo") == (ignore_case ^ invert_match)

    def test_regex(self, ignore_case, invert_match):
        matcher = compile_matcher(r"foo\d+", ignore_case, invert_match)

        assert matcher("foo123") == (True ^ invert_match)
        assert matcher("foobar") == (False ^ invert_match)

    def test_empty_pattern_matches_everything(self, ignore_case, invert_match):
        matcher = compile_matcher("", ignore_case, invert_match)

        assert matcher("anything") == (True ^ invert_match)
        assert matcher("") == (True ^ invert_match)
