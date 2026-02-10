from dataclasses import dataclass

from filetags.query.parser import Transformer as StandaloneTransformer


@dataclass
class Tag:
    name: str
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return self.name

        return f"{self.name}[{self.children}]"


@dataclass
class Xor:
    """Binary XOR - true when odd number of operands are true."""

    operands: list["Expr"]

    def __str__(self) -> str:
        return "^".join(str(op) for op in self.operands)


@dataclass
class OnlyOne:
    """Exactly one of - true when exactly one operand is true."""

    operands: list["Expr"]

    def __str__(self) -> str:
        ops = ",".join(str(op) for op in self.operands)
        return f"xor({ops})"


@dataclass
class And:
    operands: list["Expr"]

    def __str__(self) -> str:
        return ",".join(str(op) for op in self.operands)


@dataclass
class Or:
    operands: list["Expr"]

    def __str__(self) -> str:
        return "|".join(str(op) for op in self.operands)


@dataclass
class Not:
    operand: "Expr"

    def __str__(self) -> str:
        return f"!{self.operand}"


@dataclass
class Null:
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return "~"

        return f"~[{self.children}]"


@dataclass
class WildcardSingle:
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return "*"

        return f"*[{self.children}]"


@dataclass
class WildcardPath:
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return "**"

        return f"**[{self.children}]"


@dataclass
class WildcardBounded:
    max_depth: int
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return f"*{self.max_depth}*"

        return f"*{self.max_depth}*[{self.children}]"


class Transformer(StandaloneTransformer):
    # terminals
    def NAME(self, token):
        return str(token)

    def XOR_KW(self, token):
        return str(token)

    def BOUNDED_WILDCARD(self, token):
        """Gets the n from '*n*'"""
        return int(str(token)[1:-1])

    # rules
    def start(self, children):
        return children[0]

    def query(self, children):
        return children[0]

    # binary ops
    def xor_expr(self, children):
        if len(children) == 1:
            return children[0]
        return Xor(children)

    def only_one(self, children):
        # Filter out "xor" keyword string
        children = [c for c in children if c != "xor"]
        return OnlyOne(children)

    def or_expr(self, children):
        if len(children) == 1:
            return children[0]

        return Or(children)

    def and_expr(self, children):
        if len(children) == 1:
            return children[0]

        return And(children)

    # unary
    def negation(self, children):
        return Not(children[0])

    # primaries
    def grouped(self, children):
        return children[0]

    def tag(self, children):
        if len(children) == 1:
            return Tag(name=children[0])
        return Tag(name=children[0], children=children[1])

    def tag_xor(self, children):
        """Handle 'xor' used as a tag name (not the function)."""
        # children[0] is "xor" string, children[1] (if present) is the query
        if len(children) == 1:
            return Tag(name="xor")
        return Tag(name="xor", children=children[1])

    def null_expr(self, children):
        # children[0] is the NULL token, children[1] (if present) is the query
        if len(children) == 1:
            return Null()
        return Null(children=children[1])

    def wildcard_single(self, children):
        # children[0] is the SINGLE_STAR token, children[1] (if present) is the query
        if len(children) == 1:
            return WildcardSingle()
        return WildcardSingle(children=children[1])

    def wildcard_path(self, children):
        # children[0] is the DOUBLE_STAR token, children[1] (if present) is the query
        if len(children) == 1:
            return WildcardPath()
        return WildcardPath(children=children[1])

    def wildcard_bounded(self, children):
        # First child is the max_depth (from BOUNDED_WILDCARD terminal)
        max_depth = children[0]
        if len(children) == 1:
            return WildcardBounded(max_depth=max_depth)
        return WildcardBounded(max_depth=max_depth, children=children[1])


Expr = (
    Tag
    | And
    | Or
    | Xor
    | OnlyOne
    | Not
    | Null
    | WildcardSingle
    | WildcardPath
    | WildcardBounded
)


def validate_for_storage(node: Expr) -> bool:
    """Returns True if the AST only contains 'Tag' and 'And',
    since those are the only kind that are valid for storage.
    """

    match node:
        case Tag(_, None):
            return True

        case Tag(_, children):
            return validate_for_storage(children)

        case And(operands):
            return all(map(validate_for_storage, operands))

        case _:
            return False
