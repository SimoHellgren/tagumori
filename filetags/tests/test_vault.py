import json
import pytest
from filetags.src.models import Vault

test_data = '{"entries": {".\\\\files\\\\demo1.txt": ["xxx", "xx"], ".\\\\files\\\\demo2.json": [], ".\\\\files\\\\demo3.csv": ["xxx", "x", "xx"]}, "tags": [{"name": "xxx", "tag_along": ["xx"]}, {"name": "a", "tag_along": []}, {"name": "A", "tag_along": ["a"]}, {"name": "y", "tag_along": []}, {"name": "x", "tag_along": ["xxx"]}, {"name": "xx", "tag_along": ["x"]}]}'


@pytest.fixture
def vault():
    """Opens a vault with mocked data"""
    data = json.loads(test_data)
    vault = Vault.from_json(data)

    return vault


def test_open_vault(vault: Vault):
    assert vault.entries
    assert vault.tags


def test_basic_tagalong(vault: Vault):
    A = vault.get_tag("A")
    tagalongs = vault.get_tagalongs(A)

    assert {"a", "A"} == tagalongs


def test_no_tagalongs(vault: Vault):
    """Getting tagalongs for a tag without any should return just that tag's label"""
    y = vault.get_tag("y")
    tagalongs = vault.get_tagalongs(y)

    assert {"y"} == tagalongs


def test_circular_tagalongs(vault: Vault):
    """Circular tagalongs should not cause an infinite loop"""
    x = vault.get_tag("x")
    tagalongs = vault.get_tagalongs(x)

    assert {"x", "xx", "xxx"} == tagalongs


def test_add_tagalongs(vault: Vault):
    y = vault.get_tag("y")
    big_y = vault.get_tag("Y")

    assert y
    assert not big_y  # should not exist yet

    assert not y.tag_along  # should be empty

    vault.add_tagalongs("y", {"Y"})

    big_y = vault.get_tag("Y")
    assert big_y  # should be created now
    assert y.tag_along == {"Y"}


def test_add_tagalongs_preserves_existing(vault: Vault):
    x = vault.get_tag("x")
    current = set(x.tag_along)

    vault.add_tagalongs("x", {"y", "yy"})

    assert current.issubset(x.tag_along)
