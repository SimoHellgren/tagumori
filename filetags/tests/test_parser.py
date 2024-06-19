from filetags.src.parser import parse


def test_empty():
    result = parse("")

    assert result
    assert result.value == ""
    assert not result.children


def test_basic():
    result = parse("a")

    (child,) = result.children

    assert child.value == "a"


def test_basic_brackets():
    result = parse("[a]")

    (child,) = result.children

    assert child.value == "a"


def test_multiple():
    result = parse("a,b")

    a, b = result.children

    assert a.value == "a"
    assert b.value == "b"


def test_nested():
    result = parse("a[b]")

    (a,) = result.children
    (b,) = a.children

    assert a.value == "a"
    assert b.value == "b"


def test_nested_multiple():
    result = parse("a[b,c]")

    (a,) = result.children
    (b, c) = a.children

    assert a.value == "a"
    assert b.value == "b"
    assert c.value == "c"


def test_multiple_nested():
    result = parse("a[b,c],d[e,f]")

    (a, d) = result.children
    (b, c) = a.children
    (e, f) = d.children

    assert a.value == "a"
    assert b.value == "b"
    assert c.value == "c"
    assert d.value == "d"
    assert e.value == "e"
    assert f.value == "f"


def test_deeply_nested():
    result = parse("a[b[c[d[e]]]]")

    values = [n.value for n in result.descendants()]
    assert values == list("abcde")


def test_multiword():
    result = parse("test tag,other multiword tag")

    (a, b) = result.children
    assert a.value == "test tag"
    assert b.value == "other multiword tag"


def test_nested_multiword():
    result = parse("test tag[child],other multiword tag[child,multiword child]")
    (a, b) = result.children

    assert a.value == "test tag"
    assert b.value == "other multiword tag"

    (x,) = a.children
    y, z = b.children

    assert x.value == "child"
    assert y.value == "child"
    assert z.value == "multiword child"
