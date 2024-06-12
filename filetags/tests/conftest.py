import pytest
from filetags.src.models2.vault import Vault
from filetags.src.models2.node import Node


test_data = [
    {
        "name": "file1",
        "children": [
            {
                "name": "A",
                "children": [
                    {"name": "a", "children": []},
                    {"name": "b", "children": []},
                ],
            },
            {"name": "B", "children": [{"name": "a", "children": []}]},
        ],
    },
    {
        "name": "file2",
        "children": [
            {
                "name": "B",
                "children": [
                    {"name": "b", "children": []},
                ],
            }
        ],
    },
]


@pytest.fixture
def vault():
    """Opens a vault with mocked data"""
    vault = Vault.from_json(test_data)

    return vault


@pytest.fixture
def nodes() -> list[Node]:
    n1 = Node(1)
    n2 = Node(2, parent=n1)
    n3 = Node(3, parent=n2)  # leaf
    n4 = Node(4, parent=n2)  # leaf
    n5 = Node(5, parent=n1)  # leaf
    n6 = Node(6, parent=n1)
    n7 = Node(7, parent=n6)
    n8 = Node(8, parent=n7)  # leaf

    return [n1, n2, n3, n4, n5, n6, n7, n8]


@pytest.fixture
def tree(nodes: list[Node]) -> Node:
    return nodes[0]
