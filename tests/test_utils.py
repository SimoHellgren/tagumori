from filetags.utils import compile_pattern, drop, tail


def test_drop():
    data = [1, 2, 3, 4, 5]

    assert list(drop(data, 0)) == data
    assert list(drop(data, 1)) == data[1:]
    assert list(drop(data, 2)) == data[2:]
    assert list(drop(data, len(data))) == []
    assert list(drop(data, 100)) == []


def test_tail():
    data = [1, 2, 3, 4, 5]

    assert list(tail(data)) == data[1:]

    assert list(tail([])) == []


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
