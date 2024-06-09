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
            for path in child.paths():
                yield Tag(self.name, [path])

    def lowest_common_node(self, other: Self):
        """Finds the lower common node between self and other.
        Other must not be branching and self and other must start at same node.

        returns the lowest common node as well as the remainder of other
        """
        # if other has no more childen, done
        if not other.children:
            return self, None

        # get the next node to check
        (next_other,) = other.children

        next_self = next(
            (child for child in self.children if child.name == next_other.name), None
        )

        # if no next_self is found, self is the LCN
        if not next_self:
            return self, next_other

        # otherwise recurse
        return next_self.lowest_common_node(next_other)

    def merge(self, other: Self):
        """Merges other to self
        This (as well as lowest_common_node) can probably be simplified or partially combined,
        but this shall do for now.
        """

        # generate non-branching paths of other
        paths = other.paths()
        for path in paths:
            # look for a shared root
            root = self.find(path)

            # if not found, add path at self
            if not root:
                self.children.append(path)
                continue

            # otherwise, find the lowest common parent and add the remainder to its children
            parent, remainder = root.lowest_common_node(path)
            if remainder:
                parent.children.append(remainder)
