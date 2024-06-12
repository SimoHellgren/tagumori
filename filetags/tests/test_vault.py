from filetags.src.models2.vault import Vault


def test_vault(vault: Vault):
    assert vault
    assert vault._entries


def test_entries(vault: Vault):
    filenames = [a.value for a, _ in vault.entries()]
    assert "file1" in filenames
    assert "file2" in filenames


def test_find(vault: Vault):
    # TODO: fix this test
    # get nodes for setup
    file1, file2 = sorted(vault._entries, key=lambda x: x.value)

    # result1 = list(vault.find([""]))

    # assert file1.get_path(["file1", "A"])
    # assert file1 in result1
    # assert file2 not in result1
