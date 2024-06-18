from filetags.src.models.vault import Vault
from filetags.src.models.vault import Node


def test_vault(vault: Vault):
    assert vault
    assert vault._entries


def test_entries(vault: Vault):
    filenames = [a.value for a, _ in vault.entries()]
    assert "file1" in filenames
    assert "file2" in filenames


def test_find(vault: Vault):
    assert vault.find(lambda x: x.value == "file1")
    assert not vault.find(lambda x: x.value == "file999")


def test_filter_include(vault: Vault):
    # get nodes for setup
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    # empty `include` should include all files
    find_result = vault.filter()
    entries = vault.entries()
    assert list(find_result) == list(entries)

    # transpose to get a nice list of files
    (files, _) = zip(*vault.filter([[Node("A")]]))

    assert file1 in files
    assert file2 not in files

    (files, _) = zip(*vault.filter([[Node("b")]]))

    assert file1 in files
    assert file2 in files

    (files, _) = zip(*vault.filter([[Node("B", [Node("b")])]]))

    assert file1 not in files
    assert file2 in files

    result = list(vault.filter([[Node("XXX")]]))

    assert not result


def test_filter_exclude(vault: Vault):
    # get nodes for setup
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    # test(s) for excluding
    (files, _) = zip(
        *vault.filter(include=[[Node("b")]], exclude=[[Node("B", [Node("b")])]])
    )
    assert file1 in files
    assert file2 not in files

    # exclude A,B should only filter out file1
    files, _ = zip(*vault.filter(exclude=[[Node("A"), Node("B")]]))

    assert file1 not in files
    assert file2 in files

    # exclude A|B should filter out both
    result = list(vault.filter(exclude=[[Node("A")], [Node("B")]]))

    assert not result


def test_filter_or(vault: Vault):
    # get nodes for setup
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    (files, _) = zip(*vault.filter([[Node("A")], [Node("B")]]))

    assert file1 in files
    assert file2 in files


def test_rename_tag(vault: Vault):
    # get nodes for setup
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    vault.rename_tag("a", "x")

    match = lambda val: lambda x: x.value == val

    # file 1 should match x but not a
    assert not file1.find(match("a"))
    assert file1.find(match("x"))

    # file 2 didn't have a to begin with: should match neither
    assert not file2.find(match("a"))
    assert not file2.find(match("x"))


def test_add_new_entry(vault: Vault):
    entry = Node("file3", children=[Node("random new tag")])

    vault.add_entry(entry)

    filenames = [a.value for a, _ in vault.entries()]
    assert "file1" in filenames
    assert "file2" in filenames
    assert "file3" in filenames

    file1, file2, file3 = sorted(vault._entries, key=lambda x: x.value)

    assert "random new tag" in [t.value for t in file3.children]


def test_add_existing_entry(vault: Vault):
    entry = Node("file1", children=[Node("other new tag")])

    vault.add_entry(entry)  # should not do anything

    assert entry not in vault._entries
    assert not list(vault.filter([[Node("other new tag")]]))


def test_remove_entry(vault: Vault):
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)
    entry1 = vault.remove_entry("file1")

    assert entry1 is file1
    assert file1 not in vault._entries
    assert file2 in vault._entries


def test_remove_non_existent(vault: Vault):
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)
    entry2 = vault.remove_entry("file999")

    assert not entry2
    assert file1 in vault._entries
    assert file2 in vault._entries


def test_add_tag(vault: Vault):
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    # new top-level tag
    tag = Node("file1", [Node("C", [Node("c")])])

    vault.add_tag(tag)

    assert [c.value for c in file1.children] == ["A", "B", "C"]


def test_add_tag_new_file(vault: Vault):
    # new file should get added
    tag = Node("file3", [Node("X")])

    vault.add_tag(tag)

    file3 = vault.find(lambda x: x.value == "file3")

    assert file3
    (x,) = file3.children

    assert x.value == "X"


def test_add_nested_tag(vault: Vault):
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    # new top-level tag
    tag = Node("file1", [Node("A", [Node("c")])])

    vault.add_tag(tag)
    a, b = file1.children

    assert [c.value for c in file1.children] == ["A", "B"]
    assert "c" in [c.value for c in a.children]


def test_add_nested_tag(vault: Vault):
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    # new nested tag
    tag = Node("file1", [Node("A", [Node("c")])])

    vault.add_tag(tag)
    a, b = file1.children

    assert [c.value for c in file1.children] == ["A", "B"]
    assert "c" in [c.value for c in a.children]


def test_add_existing_tag(vault: Vault):
    before, _ = sorted(vault._entries, key=lambda x: x.value)

    # existing tag
    tag = Node("file1", [Node("A", [Node("b")])])

    vault.add_tag(tag)

    after, _ = sorted(vault._entries, key=lambda x: x.value)

    assert list(before.preorder()) == list(after.preorder())


def test_remove_tag(vault: Vault):
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    a, b = file1.children

    vault.remove_tag(Node("file1", [Node("A")]))

    assert a not in file1.children


def test_remove_nested_tag(vault: Vault):
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    A, B = file1.children
    a, b = A.children

    vault.remove_tag(Node("file1", [Node("A", [Node("a")])]))

    assert A in file1.children
    assert a not in A.children
    assert b in A.children


def test_remove_nonexistent_tag(vault: Vault):
    before, _ = sorted(vault._entries, key=lambda x: x.value)

    tag = Node("file1", [Node("A", [Node("XXX")])])

    vault.remove_tag(tag)

    after, _ = sorted(vault._entries, key=lambda x: x.value)

    assert list(before.preorder()) == list(after.preorder())


def test_get_tagalongs(vault: Vault):
    res = vault.get_tagalongs("AAA")

    assert res == {"AAA", "BBB", "CCC"}


def test_circular_tagalongs(vault: Vault):
    res = vault.get_tagalongs("rock")

    assert res == {"rock", "paper", "scissors"}


def test_no_tagalongs(vault: Vault):
    res = vault.get_tagalongs("just me, I'm afraid")

    assert res == {"just me, I'm afraid"}


def test_add_tag_with_tagalong(vault: Vault):
    tag = Node("file1", [Node("paper")])

    vault.add_tag(tag)

    file1, *rest = sorted(vault._entries, key=lambda x: x.value)

    values = [c.value for c in file1.children]
    assert "rock" in values
    assert "paper" in values
    assert "scissors" in values
