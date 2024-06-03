from filetags.src.models import Tag


def test_basic_tag():
    t = Tag("test")

    assert t.name == "test"
    assert t.tag_along == set()

    assert t.__json__() == {"name": "test", "tag_along": set()}


def test_tag_with_tagalongs():
    t = Tag("test", ["test2", "test3"])

    assert t.name == "test"
    assert t.tag_along == ["test2", "test3"]

    assert t.__json__() == {"name": "test", "tag_along": ["test2", "test3"]}


def test_tag_sets():
    """sets should be compared by tag name"""
    a1, a2 = Tag("a"), Tag("a")
    b1, b2 = Tag("b"), Tag("b")

    set1 = {a1, b1}
    set2 = {a2, b2}

    # ensure objects are different
    assert id(a1) != id(a2)
    assert id(b1) != id(b2)
    assert set1 == set2
