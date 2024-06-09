import json
from filetags.src.models2.tag import Tag


class Vault:
    def __init__(self, entries: list[Tag]):
        self._entries = entries

    def entries(self):
        for file in self._entries:
            yield file.name, [str(child) for child in file.children]

    def find(self, tag: Tag):
        for file in self._entries:
            if file.contains(tag):
                yield file

    def add_entry(self, name: str):
        entry = Tag(name)
        self._entries.append(entry)

    def remove_entry(self, name: str):
        self._entries = [file for file in self._entries if file.name != name]

    def add_tags(self, filename: str, tags: list[Tag]):
        # constructing "Tag(filename)" twice is kinda silly
        (entry,) = self.find(Tag(filename))

        entry.merge(Tag(filename, tags))

        return entry


def parse(tag: dict):
    name = tag["name"]
    children = tag["children"]
    child_tags = [parse(t) for t in children]
    return Tag(name, child_tags)


if __name__ == "__main__":
    with open("vault2.json") as f:
        data = json.load(f)

    vault = Vault([parse(e) for e in data])

    for file, tags in vault.entries():
        print(file, tags)
