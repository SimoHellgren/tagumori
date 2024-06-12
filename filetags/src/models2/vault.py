from typing import Generator, Self
import json
from filetags.src.models2.node import Node

# TODO: consider implementing Vault as just a Node with a root value
# this would likely need the implementation of a wilcard search to enable
# skipping levels


class Vault:
    def __init__(self, entries: Node):
        self._entries = entries

    def entries(self) -> Generator[tuple[str, list[Node]], None, None]:
        for file in self._entries:
            yield file, file.children

    def find(self, path: list[str]):
        for file, children in self.entries():
            if any(c.get_path(path) for c in children):
                yield file, children

    @classmethod
    def from_json(cls, data: list) -> Self:
        return cls(parse(e) for e in data)


def parse(entry: dict):
    name = entry["name"]
    children = entry["children"]
    child_tags = [parse(t) for t in children]
    return Node(name, child_tags)


if __name__ == "__main__":
    with open("vault2.json") as f:
        data = json.load(f)

    vault = Vault.from_json(data)

    for file, tags in vault.find(["p1"]):
        print(file.value, list(map(str, tags)))
