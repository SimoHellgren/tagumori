import json
import pytest
from filetags.src.models import Vault

# TODO: new test data for new models

test_data = {
    "entries": {
        "demo1": ["a"],
        "demo2": ["y"],
        "demo3": ["a", "xxx", "x", "xx"],
        "demo4": [],
    },
    "tags": [
        {"name": "a", "tag_along": []},
        {"name": "A", "tag_along": ["a"]},
        {"name": "y", "tag_along": []},
        # circular tag-alongs
        # also useful for recursive tag-along tests
        {"name": "x", "tag_along": ["xxx"]},
        {"name": "xx", "tag_along": ["x"]},
        {"name": "xxx", "tag_along": ["xx"]},
    ],
}


@pytest.fixture
def vault():
    """Opens a vault with mocked data"""
    vault = Vault.from_json(test_data)

    return vault
