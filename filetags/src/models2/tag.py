from typing import Optional, Self


class Tag:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []

    def __str__(self):
        kids = ",".join(
            str(child) for child in sorted(self.children, key=lambda x: x.name)
        )
        return f"{self.name}" + (f"[{kids}]" if kids else "")

    def __repr__(self):
        return f"Tag({self})"

    def __json__(self):
        return {"name": self.name, "children": self.children}

    def find(self, tag: Self) -> Optional[Self]:
        """Depth-first search"""
        # None matches any tag
        if tag.name == self.name or tag.name is None:
            return self

        for child in self.children:
            res = child.find(tag)
            if res:
                return res

    def contains(self, tag: Self) -> bool:
        node = self.find(tag)

        # top level node not matched
        if not node:
            return False

        # no more children to search
        if not tag.children:
            return True

        # all children must match
        return all(node.find(child) for child in tag.children)

    def paths(self):
        """Returns all paths from self to leaves
        e.g. path A[a,b[c]] -> [[A,a], [A,b,c]]
        """

        if not self.children:
            yield Tag(self.name)

        for child in self.children:
            yield Tag(self.name, list(child.paths()))
