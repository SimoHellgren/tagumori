import json
from filetags.src.models2.tag import Tag


class Vault:
    def __init__(self, entries):
        self._entries = entries

    def entries(self):
        for file in self._entries:
            print(file.name, [str(child) for child in file.children])

        print()

    def add_entry(self, name: str):
        entry = Tag(name)
        self._entries.append(entry)

    def remove_entry(self, name: str):
        self._entries = [file for file in self._entries if file.name != name]


def parse(tag: dict):
    name = tag["name"]
    children = tag["children"]
    child_tags = [parse(t) for t in children]
    return Tag(name, child_tags)


if __name__ == "__main__":
    with open("vault2.json") as f:
        data = json.load(f)

    vault = Vault([parse(e) for e in data])

    vault.entries()

    vault.add_entry("file3")

    vault.entries()

    vault.remove_entry("file2")

    vault.entries()
