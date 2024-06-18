from typing import Generator, Self, Optional, Callable
import json
from filetags.src.models.node import Node
from filetags.src.utils import flatten

# TODO: consider implementing Vault as just a Node with a root value
# this would likely need the implementation of a wilcard search to enable
# skipping levels


class Vault:
    def __init__(self, entries: list[Node], tagalongs: list):
        self._entries: list[Node] = entries
        self.tagalongs = tagalongs

    def entries(self) -> Generator[tuple[Node, list[Node]], None, None]:
        for file in self._entries:
            yield file, file.children

    def find(self, pred: Callable) -> Node | None:
        return next(filter(pred, self._entries), None)

    def filter(
        self,
        include: Optional[list[list[Node]]] = None,
        exclude: Optional[list[list[Node]]] = None,
    ):
        for file, children in self.entries():
            # skip if exclude
            if exclude and any(
                all(n.is_subtree(file) for n in excl) for excl in exclude
            ):
                continue

            # yield if include
            if not include or any(
                all(n.is_subtree(file) for n in incl) for incl in include
            ):
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

        # add tagalongs
        for t in tag.descendants():
            tagalongs = self.get_tagalongs(t.value) - {t.value}  # clunky
            for ta in tagalongs:
                if ta not in [n.value for n in t.siblings()]:
                    t.parent.add_child(Node(ta))

        if not file:
            self.add_entry(tag)
            return

        file.merge(tag)

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

        # rename also tagalongs
        self.tagalongs = [(new, b) if a == tag else (a, b) for a, b in self.tagalongs]
        self.tagalongs = [(a, new) if b == tag else (a, b) for a, b in self.tagalongs]

    def tags(self) -> set[Node]:
        return set(
            flatten((x.value for x in file.descendants()) for file in self._entries)
        )

    def add_tagalong(self, tag: str, tagalong: str):
        pair = [tag, tagalong]

        if pair not in self.tagalongs:
            self.tagalongs.append(pair)

    def remove_tagalong(self, tag: str, tagalong: str):
        pair = [tag, tagalong]

        self.tagalongs = [p for p in self.tagalongs if p != pair]

    def get_tagalongs(self, tag: str, seen: set = None) -> set[str]:  # type: ignore
        if not seen:
            seen = set()

        seen.add(tag)

        for a, b in self.tagalongs:
            if b in seen or a != tag:
                continue

            # recurse
            self.get_tagalongs(b, seen)
        return seen

    @classmethod
    def from_json(cls, data: list) -> Self:
        return cls([parse(e) for e in data["entries"]], data["tagalongs"])

    def __json__(self):
        return {"entries": self._entries, "tagalongs": self.tagalongs}

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
