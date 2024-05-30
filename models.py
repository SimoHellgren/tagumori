from typing import Optional, Set, List
from collections import defaultdict
from pathlib import Path
import json
import click
from utils import flatten


class Vault:
    def __init__(self, filename: str):
        self.filename = filename

        with open(filename, "r") as f:

            data = json.load(f)

            self.tags = data["tags"]

            converted_sets = {k: set(v) for k, v in data["entries"].items()}
            self.entries = defaultdict(set, converted_sets)

    def files(self, tags: Optional[List[Set[str]]] = None) -> List[str]:
        return [
            file
            for file, f_tags in self.entries.items()
            if any(t.issubset(f_tags) for t in tags or []) or not tags
        ]

    def list_tags(self) -> List[str]:
        return sorted(set(flatten(self.entries.values())))

    def items(self):
        return self.entries.items()

    def add_tags(self, file: str, tags: Set[str]):
        current_tags = set(self.tags)
        new_tags = tags - current_tags

        for tag in new_tags:
            self.create_tag(tag)

        self.entries[file] |= tags

    def remove_tags(self, file: str, tags: Set[str]):
        self.entries[file] -= tags

    def create_tag(self, tag):
        if tag in self.tags:
            print(tag, "already exists")

        else:
            self.tags.append(tag)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, trace):
        # only write if no exception
        if exc_type is None:
            with open(self.filename, "w") as f:
                f.write(self.to_json(indent=2))

    def to_json(self, **kwargs):
        return json.dumps(
            {
                "entries": {name: list(tags) for name, tags in self.entries.items()},
                "tags": self.tags,
            },
            **kwargs,
        )

    @staticmethod
    def init(name):
        path = Path(name)

        if path.exists():
            click.echo(f"{name} already exists.")

        else:
            with open(path, "w") as f:
                json.dump(
                    {
                        "entries": {},
                        "tags": {},
                    },
                    f,
                    indent=2,
                )


# custom classes for click
class DelimitedSet(click.ParamType):
    name = "delimited set"

    def __init__(self, *args, delimiter=",", **kwargs):
        super().__init__(*args, **kwargs)
        self.delimiter = delimiter

    def convert(self, value, param, ctx):
        if isinstance(value, set):
            return True

        try:
            return {elem.strip() for elem in value.split(self.delimiter)}

        except ValueError:
            self.fail(
                f"Couldn't parse set from {value} with delimiter {self.delimiter}",
                param,
                ctx,
            )
