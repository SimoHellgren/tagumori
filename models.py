from typing import Optional, Set, List
from collections import defaultdict
from pathlib import Path
import json
import click
from utils import flatten, find


class Tag:
    def __init__(self, name, tag_along=None):
        self.name = name
        self.tag_along = tag_along or []

    def to_dict(self):
        # bit of an ugly hack that ensures that this converts to JSON properly.
        return {"name": self.name, "tag_along": list(self.tag_along)}

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        return self.name == other.name

    def __hash__(self):
        return self.name.__hash__()


class Vault:
    def __init__(self, filename: str):
        self.filename = filename

        with open(filename, "r") as f:

            data = json.load(f)

            self.tags = {Tag(tag["name"], tag["tag_along"]) for tag in data["tags"]}

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

    def get_tag(self, tag: str) -> Optional[Tag]:
        return find(lambda x: x.name == tag, self.tags)

    def add_tags(self, file: str, tags: Set[str]):
        # create new tags if needed
        current_tags = set(t.name for t in self.tags)
        new_tags = tags - current_tags

        for tag in new_tags:
            self.create_tag(tag)

        # for each tag, find tagalongs
        for tag in tags:
            tag_obj = self.get_tag(tag)
            with_tagalongs = self.get_tagalongs(tag_obj)

            self.entries[file] |= with_tagalongs

    def remove_tags(self, file: str, tags: Set[str]):
        self.entries[file] -= tags

    def create_tag(self, tag: str, tag_along: list = None):
        # generate tag objects for tag and tag_alongs
        objects = {Tag(tag, tag_along)} | {Tag(ta) for ta in tag_along or []}

        for tag_obj in objects:
            if tag_obj in self.tags:
                print(tag_obj, "already exists")

            else:
                self.tags.add(tag_obj)

    def get_tagalongs(self, tag: Tag, seen: set = None):
        """Recursively find all tag-alongs for a tag"""
        # keep track of already seen tags to avoid infinite loops
        if not seen:
            seen = set()

        seen.add(tag.name)

        result = set([tag.name, *tag.tag_along])
        for ta in tag.tag_along:
            if ta in seen:
                continue

            ta_obj = self.get_tag(ta)
            next_tas = self.get_tagalongs(ta_obj, seen)
            result |= next_tas

        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, trace):
        # only write if no exception
        if exc_type is None:
            with open(self.filename, "w") as f:
                f.write(self.to_json(indent=2))

    def to_json(self, **kwargs):
        t = {
            "entries": {name: list(tags) for name, tags in self.entries.items()},
            "tags": [tag.to_dict() for tag in self.tags],
        }

        return json.dumps(
            t,
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
