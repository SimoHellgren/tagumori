from filetags.src.models2.vault import Vault
from filetags.src.models2.vault import Node


def test_vault(vault: Vault):
    assert vault
    assert vault._entries


def test_entries(vault: Vault):
    filenames = [a.value for a, _ in vault.entries()]
    assert "file1" in filenames
    assert "file2" in filenames


def test_find(vault: Vault):
    # get nodes for setup
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    # transpose to get a nice list of files
    (files, _) = zip(*vault.find(["A"]))

    assert file1 in files
    assert file2 not in files

    (files, _) = zip(*vault.find(["b"]))

    assert file1 in files
    assert file2 in files

    (files, _) = zip(*vault.find(["B", "b"]))

    assert file1 not in files
    assert file2 in files

    result = list(vault.find(["XXX"]))

    assert not result

    # test(s) for excluding
    (files, _) = zip(*vault.find(include=["b"], exclude=["B", "b"]))
    assert file1 in files
    assert file2 not in files


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

    assert list(vault.find(["random new tag"]))


def test_add_existing_entry(vault: Vault):
    entry = Node("file1", children=[Node("other new tag")])

    vault.add_entry(entry)  # should not do anything

    assert entry not in vault._entries
    assert not list(vault.find(["other new tag"]))


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
