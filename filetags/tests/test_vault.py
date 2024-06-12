from filetags.src.models2.vault import Vault


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
