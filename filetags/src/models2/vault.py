from typing import Generator, Self, Optional
import json
from filetags.src.models2.node import Node

# TODO: consider implementing Vault as just a Node with a root value
# this would likely need the implementation of a wilcard search to enable
# skipping levels


class Vault:
    def __init__(self, entries: list[Node]):
        self._entries = entries

    def entries(self) -> Generator[tuple[Node, list[Node]], None, None]:
        for file in self._entries:
            yield file, file.children

    def find(
        self, include: Optional[list[str]] = None, exclude: Optional[list[str]] = None
    ):
        # TODO: consider renaming this to e.g. `filter` - `find` could be useful otherwise
        for file, children in self.entries():
            # skip if exclude
            if exclude and next(file.find_path(exclude), None):
                continue

            # yield if include
            if include and next(file.find_path(include), None):
                yield file, children

    def add_entry(self, entry: Node):
        if not entry.value in [e.value for e in self._entries]:
            self._entries.append(entry)

    def remove_entry(self, name: str) -> Node | None:
        entry = next((e for e in self._entries if e.value == name), None)
        self._entries = [e for e in self._entries if e is not entry]
        return entry

    def rename_tag(self, tag: str, new: str):
        """Renames all instances of tag"""
        for file, _ in self.entries():
            nodes = file.find_all(lambda x: x.value == tag)
            for node in nodes:
                node.value = new

    @classmethod
    def from_json(cls, data: list) -> Self:
        return cls([parse(e) for e in data])

    def __json__(self):
        return self._entries


class VaultJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()

        return super().default(obj)


def parse(entry: dict):
    name = entry["name"]
    children = entry["children"]
    child_tags = [parse(t) for t in children]
    return Node(name, child_tags)


if __name__ == "__main__":
    with open("vault2.json") as f:
        data = json.load(f)

    vault = Vault.from_json(data)

    for file, tags in vault.entries():
        print(file.value, list(map(str, tags)))
