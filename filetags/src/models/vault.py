from typing import Generator, Self, Optional, Callable
import json
from filetags.src.models.node import Node

# TODO: consider implementing Vault as just a Node with a root value
# this would likely need the implementation of a wilcard search to enable
# skipping levels

# TODO: tag-alongs


class Vault:
    def __init__(self, entries: list[Node]):
        self._entries: list[Node] = entries

    def entries(self) -> Generator[tuple[Node, list[Node]], None, None]:
        for file in self._entries:
            yield file, file.children

    def find(self, pred: Callable) -> Node | None:
        return next(filter(pred, self._entries), None)

    def filter(
        self, include: Optional[list[str]] = None, exclude: Optional[list[str]] = None
    ):
        for file, children in self.entries():
            # skip if exclude
            if exclude and next(file.find_path(exclude), None):
                continue

            # yield if include
            if not include or next(file.find_path(include), False):
                yield file, children

    def add_entry(self, entry: Node):
        if not entry.value in [e.value for e in self._entries]:
            self._entries.append(entry)

    def remove_entry(self, name: str) -> Node | None:
        entry = next((e for e in self._entries if e.value == name), None)
        self._entries = [e for e in self._entries if e is not entry]
        return entry

    def add_tag(self, tag: Node):
        """Node should start at the file-level"""

        # find the file of interest
        file = next((f for f in self._entries if f.value == tag.value), None)

        if not file:
            return

        # find a place for each path of tag
        for path in tag.paths_down():
            # TODO: this is a bit wonky - there are two notions of `path` in Node:
            # 1. path is of type list[T]
            # 2. path is of type tuple[Node]
            path_strings = [e.value for e in path]
            node, remainder = file.get_path_remainder(path_strings)

            # if no remainder, the tag already exists
            if node and remainder:
                # also a bit silly that we construct a completely new Node here,
                # when we already provide one as an input.
                node.add_child(Node.from_path(remainder))

    def remove_tag(self, tag: Node):
        file = next((f for f in self._entries if f.value == tag.value), None)

        if not file:
            return

        for path in tag.paths_down():
            path_string = [e.value for e in path]

            if node := file.get_path(path_string):
                node.detach()

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

    def to_json(self, **kwargs):
        return json.dumps(self, cls=VaultJSONEncoder, **kwargs)


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
