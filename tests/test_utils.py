from tagumori.utils import compile_pattern


def test_compile_pattern_basic():
    pattern = compile_pattern("foo", ignore_case=False)

    assert pattern.search("foo")
    assert pattern.search("foobar")
    assert not pattern.search("bar")


def test_compile_pattern_case_sensitive():
    pattern = compile_pattern("foo", ignore_case=False)

    assert pattern.search("foo")
    assert not pattern.search("FOO")
    assert not pattern.search("Foo")


def test_compile_pattern_ignore_case():
    pattern = compile_pattern("foo", ignore_case=True)

    assert pattern.search("foo")
    assert pattern.search("FOO")
    assert pattern.search("Foo")


def test_compile_pattern_regex():
    pattern = compile_pattern(r"foo\d+", ignore_case=False)

    assert pattern.search("foo123")
    assert not pattern.search("foobar")


def test_compile_pattern_empty_returns_none():
    assert compile_pattern("", ignore_case=False) is None
    assert compile_pattern("", ignore_case=True) is None
