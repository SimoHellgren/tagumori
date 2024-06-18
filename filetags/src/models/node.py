from typing import Self, TypeVar, Generic, Optional, Generator, Callable, Iterator
from filetags.src.utils import tail, find

T = TypeVar("T")


class Node(Generic[T]):
    def __init__(
        self,
        value: T,
        children: Optional[list[Self]] = None,
        parent: Optional[Self] = None,
    ):
        self.value = value
        self.parent = parent
        if parent:
            parent.add_child(self)

        self.children: list[Self] = children or []
        for child in self.children:
            child.parent = self

    def iter_path_reverse(self) -> Generator[Self, None, None]:
        node: Self | None = self
        while node is not None:
            yield node
            node = node.parent

    @property
    def root(self):
        node = self
        while node.parent:
            node = node.parent

        return node

    def path(self) -> tuple[Self, ...]:
        return tuple(reversed(list(self.iter_path_reverse())))

    def paths_down(self) -> Generator[tuple[Self, ...], None, None]:
        """Yield all paths to leaves from self"""
        if not self.children:
            yield self,

        else:
            for child in self.children:
                for p in child.paths_down():
                    yield tuple([self, *p])

    def find_all(self, pred: Callable[[Self], bool]) -> Iterator[Self]:
        return filter(pred, self.preorder())

    def find(self, pred: Callable[[Self], bool]) -> Optional[Self]:
        return next(self.find_all(pred), None)

    def glob(self, path: list[str]) -> Generator[tuple[Self, ...], None, None]:
        """Wilcard path search (though only supports * for now)"""
        for p in self.paths_down():
            # if there's more path to check than remaining, can't be a match
            # (there's probably a nicer way to implement this, perhaps zip_longest)
            if len(p) < len(path):
                continue

            # otherwise, the whole path must match (or be wildcard)
            if all(a and (a.value == b or b == "*") for a, b in zip(p, path)):
                yield p

    def find_path(self, path: list[str]):
        """Otherwise same as glob, but could start from arbitrary node.
        Debatable whether this should be in the Node class, or just be the caller's
        responsibility.
        """
        first, *_ = path
        node = self.find(lambda x: x.value == first)

        if node:
            yield from node.glob(path)

    def get_path(self, path: list[T]) -> Self | None:
        """Starting from self, traverse path and return node if found.
        Essentially, a stricter version of get_path_remainder:
        unless the whole path is found, None is returned
        """
        node, remainder = self.get_path_remainder(path)
        return None if remainder else node

    def get_path_remainder(self, path: list[T]) -> tuple[Self | None, list[T]]:
        """Starting from self, traverse path and return last node that is found.
        Additionally return remainder of / unfound path.

        Essentially, returns the lowest common parent of the tree and the given path.
        """
        if not path:
            return None, path

        first, *rest = path

        # path must start at current node
        if not first == self.value:
            return None, path

        node = self
        for p in rest:
            next_node = next((c for c in node.children if c.value == p), None)

            if not next_node:
                return node, rest

            node = next_node
            _, *rest = rest

        return node, rest

    @classmethod
    def from_path(cls, path: list[T]):
        nodes = [cls(p) for p in path]
        for parent, child in zip(nodes, nodes[1:]):
            parent.add_child(child)

        return nodes[0]

    def ancestors(self) -> tuple[Self, ...]:
        """returns path from root to self"""
        if not self.parent:
            return tuple()

        return self.parent.path()

    def descendants(self) -> tuple[Self, ...]:
        return tuple(tail(self.preorder()))

    def preorder(self) -> Generator[Self, None, None]:
        """Iterate over the tree with preorder DFS"""
        yield self
        for child in self.children:
            yield from child.preorder()

    def add_child(self, other: Self):
        if other.value not in {c.value for c in self.children}:
            self.children.append(other)
            other.parent = self

    def siblings(self) -> list[Self]:
        if not self.parent:
            # root node has no siblings
            return []

        return [c for c in self.parent.children if c is not self]

    def leaves(self):
        return tuple(n for n in self.preorder() if n.is_leaf)

    def attach(self, parent: Self):
        parent.add_child(self)

    def detach(self):
        """Detaches from parent"""
        # a clever trick would be to implement this as just self.siblings(), but perhaps best to be explicit here
        self.parent.children = [c for c in self.parent.children if c is not self]
        self.parent = None

    @property
    def is_leaf(self):
        return not bool(self.children)

    @property
    def is_root(self):
        return self.parent is None

    def __str__(self) -> str:
        """Return a string-representation of the whole tree"""
        children = ",".join(
            str(child) for child in sorted(self.children, key=lambda x: x.value)
        )
        return f"{self.value}" + (f"[{children}]" if children else "")

    def __repr__(self) -> str:
        return f"Node({self.value})"

    def __json__(self):
        return {"name": self.value, "children": self.children}

    def is_rooted_subtree(self, other: Self) -> bool:
        """Checks if structure of self is found in other. Must match also at root.
        Other may have paths not found in self (e.g. extra children on same level)
        """
        # roots must match
        if not self.value == other.value:
            return False

        # all children of self must be subtrees of some child of other
        for child in self.children:
            if not any(child.is_rooted_subtree(c) for c in other.children):
                return False

        # no recursive child returned False if we got here
        return True

    def is_subtree(self, other: Self) -> bool:
        """A more lenient version of `is_rooted_subtree` which allows
        self to be a subtree of any node in other
        """

        return any(self.is_rooted_subtree(o) for o in other.preorder())

    def merge(self, other: Self):
        """recursively merges other into self"""

        # must have same root
        if self.value != other.value:
            return

        for child in other.children:
            next_root = find(lambda x: x.value == child.value, self.children)

            if next_root:
                next_root.merge(child)

            else:
                self.add_child(child)
