from filetags.src.models import Vault


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


def test_files_all(vault: Vault):
    files = [
        "demo1",
        "demo2",
        "demo3",
    ]

    vault_ls = vault.files()

    for file in files:
        assert file in vault_ls


def test_files_filters(vault: Vault):
    # select single tag
    assert sorted(vault.files([{"a"}])) == ["demo1", "demo3"]

    # select and'd tags
    assert vault.files([{"x", "xx"}]) == ["demo3"]

    # select or'd tags
    assert sorted(vault.files([{"x"}, {"y"}])) == ["demo2", "demo3"]

    # exclude single tag
    assert sorted(vault.files(exclude=[{"a"}])) == ["demo2", "demo4"]

    # exclude and'd tags
    assert sorted(vault.files(exclude=[{"a", "x"}])) == ["demo1", "demo2", "demo4"]

    # exclude or'd tags
    assert vault.files(exclude=[{"a"}, {"y"}]) == ["demo4"]

    # both select and exclude
    assert vault.files(select=[{"a"}], exclude=[{"x"}]) == ["demo1"]


def test_delete_tag(vault: Vault):
    vault.delete_tag("x")

    # tag should no longer exist
    assert not vault.get_tag("x")

    # no files should be tagged with tag
    assert not vault.files(select=[{"x"}])

    # tag shuold not be any other tag's tagalong
    for tag in vault.tags:
        assert "x" not in tag.tag_along

    # other tags should still be present
    assert vault.get_tag("y")
    assert vault.files([{"y"}])
