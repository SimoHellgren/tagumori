import json
from filetags.src.models.node import Node
from filetags.src.models.vault import Vault, VaultJSONEncoder


def nodes_equal(a: Node, b: Node):
    """helper function to recursively check equality of nodes"""
    if a.value != b.value:
        return False

    if len(a.children) != len(b.children):
        return False

    return all(nodes_equal(x, y) for x, y in zip(a.children, b.children))


def test_node(nodes: list[Node]):
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    assert n8.__json__() == {"name": 8, "children": []}
    assert n7.__json__() == {"name": 7, "children": [n8]}
    assert n6.__json__() == {"name": 6, "children": [n7]}

    assert n2.__json__() == {"name": 2, "children": [n3, n4]}


def test_vault(vault: Vault):
    result = vault.__json__()
    assert result
    assert isinstance(result, dict)
    assert len(result) == 2


def test_vault_to_json(vault: Vault):
    """Converts vault to json and back, and checks that the result is the same"""
    json_string = vault.to_json()

    vault2 = Vault.from_json(json.loads(json_string))

    node1 = Node("root", vault._entries)
    node2 = Node("root", vault2._entries)

    assert nodes_equal(node1, node2)


def test_empty_vault():
    vault = Vault([], [])

    assert vault
    assert vault.__json__() == {"entries": [], "tagalongs": []}


def test_encoder(vault: Vault, nodes: list[Node]):
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    value = json.dumps(n2, cls=VaultJSONEncoder)
    assert (
        value
        == '{"name": 2, "children": [{"name": 3, "children": []}, {"name": 4, "children": []}]}'
    )

    # for now, just test that the conversion works
    value = json.dumps(vault, cls=VaultJSONEncoder)
    assert value

    # also check that you can convert back to vault
    new_vault = Vault.from_json(json.loads(value))
    assert new_vault
