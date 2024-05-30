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
            converted_sets = {k: set(v) for k, v in json.load(f).items()}
            self.data = defaultdict(set, converted_sets)

    def files(self, tags: Optional[List[Set[str]]] = None) -> List[str]:
        return [
            file
            for file, f_tags in self.data.items()
            if any(t.issubset(f_tags) for t in tags or []) or not tags
        ]

    def tags(self) -> List[str]:
        return sorted(set(flatten(self.data.values())))

    def items(self):
        return self.data.items()

    def add_tags(self, file: str, tags: Set[str]):
        self.data[file] |= tags

    def remove_tags(self, file: str, tags: Set[str]):
        self.data[file] -= tags

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, trace):
        # only write if no exception
        if exc_type is None:
            with open(self.filename, "w") as f:
                # default handles conversion of sets to lists.
                # possibly need to do something more elegant later.
                json.dump(self.data, f, indent=2, default=list)

    @staticmethod
    def init(name):
        path = Path(name)

        if path.exists():
            click.echo(f"{name} already exists.")

        else:
            with open(path, "w") as f:
                json.dump({}, f, indent=2)


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
