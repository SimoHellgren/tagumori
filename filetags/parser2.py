from dataclasses import dataclass
from pathlib import Path

import lark

GRAMMAR = Path(__file__).parent / "grammar.lark"

parser = lark.Lark(GRAMMAR.read_text(), parser="lalr")


@dataclass
class Tag:
    name: str
    children: "Expr | None" = None


@dataclass
class Xor:
    """Binary XOR - true when odd number of operands are true."""
    operands: list["Expr"]


@dataclass
class OnlyOne:
    """Exactly one of - true when exactly one operand is true."""
    operands: list["Expr"]


@dataclass
class And:
    operands: list["Expr"]


@dataclass
class Or:
    operands: list["Expr"]


@dataclass
class Not:
    operand: "Expr"


@dataclass
class Null:
    children: "Expr | None" = None


@dataclass
class WildcardSingle:
    children: "Expr | None" = None


@dataclass
class WildcardPath:
    children: "Expr | None" = None


@dataclass
class WildcardBounded:
    max_depth: int
    children: "Expr | None" = None


class Transformer(lark.Transformer):
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
        if len(children) == 0:
            return Null()
        return Null(children=children[0])

    def wildcard_single(self, children):
        if len(children) == 0:
            return WildcardSingle()
        return WildcardSingle(children=children[0])

    def wildcard_path(self, children):
        if len(children) == 0:
            return WildcardPath()
        return WildcardPath(children=children[0])

    def wildcard_bounded(self, children):
        # First child is the max_depth (from BOUNDED_WILDCARD terminal)
        max_depth = children[0]
        if len(children) == 1:
            return WildcardBounded(max_depth=max_depth)
        return WildcardBounded(max_depth=max_depth, children=children[1])


Expr = (
    Tag | And | Or | Xor | OnlyOne | Not | Null | WildcardSingle | WildcardPath | WildcardBounded
)

p = parser.parse
t = Transformer().transform


if __name__ == "__main__":
    import sys

    x = sys.argv[1]
    print(t(p(x)))
