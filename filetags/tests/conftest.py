import pytest
from filetags.src.models2.vault import Vault


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
