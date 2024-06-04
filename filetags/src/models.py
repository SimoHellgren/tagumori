from typing import Optional, Set, List, DefaultDict
from collections import defaultdict
import json
import click
from filetags.src.utils import flatten, find


class VaultJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # use __json__ method if found
        if hasattr(obj, "__json__"):
            return obj.__json__()

        # encode sets as lists
        if isinstance(obj, set):
            return list(obj)

        return super().default(obj)


class Tag:
    def __init__(self, name, tag_along=None):
        self.name = name
        self.tag_along = tag_along or set()

    def __json__(self):
        """Returns a json-serializable version of self"""
        return {"name": self.name, "tag_along": self.tag_along}

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        return self.name == other.name

    def __hash__(self):
        return self.name.__hash__()


class Vault:
    def __init__(self, entries: DefaultDict[str, set], tags: Set[Tag]):
        self.entries = entries
        self.tags = tags

    @classmethod
    def from_json(cls, data):
        tags = {Tag(tag["name"], set(tag["tag_along"])) for tag in data["tags"]}

        converted_sets = {k: set(v) for k, v in data["entries"].items()}
        entries = defaultdict(set, converted_sets)
        return cls(entries, tags)

    def files(
        self,
        select: Optional[List[Set[str]]] = None,
        exclude: Optional[List[Set[str]]] = None,
    ) -> List[str]:

        return [
            file
            for file, f_tags in self.entries.items()
            if any(t.issubset(f_tags) for t in select or [])
            or not select
            and not any(t.issubset(f_tags) for t in exclude or [])
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

    def add_tagalongs(self, tag: str, tag_alongs: set):
        tag_obj = self.get_tag(tag)

        for ta in tag_alongs:
            if not self.get_tag(ta):
                self.tags.add(Tag(ta))

        tag_obj.tag_along |= tag_alongs

    def get_tagalongs(self, tag: Tag, seen: set = None) -> Set[str]:
        """Recursively find all tag-alongs for a tag"""
        # keep track of already seen tags to avoid infinite loops
        if not seen:
            seen = set()

        # add current tag to result set
        seen.add(tag.name)

        for ta in tag.tag_along:
            # skip if already seen
            if ta in seen:
                continue

            # find the tag-alongs of current tag-along and recurse
            ta_obj = self.get_tag(ta)
            self.get_tagalongs(ta_obj, seen)

        return seen

    def to_json(self, **kwargs) -> str:
        return json.dumps(self, cls=VaultJSONEncoder, **kwargs)

    def __json__(self):
        """Returns a json-serializable version of self"""
        return {
            "entries": self.entries,
            "tags": self.tags,
        }


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
