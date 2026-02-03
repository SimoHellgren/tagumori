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


# Query plan stuff
@dataclass
class SegmentTag:
    name: str


@dataclass
class SegmentWildCardSingle:
    """Matches any single tag (*)"""

    pass


@dataclass
class SegmentWildCardPath:
    """Matches zore or more tags (**)"""

    pass


@dataclass
class SegmentWildCardBounded:
    """Matches up to n tags (*n*)"""

    max_depth: int


@dataclass
class SegmentNull:
    """Matches root/leaf nodes (~[...] / ...[~])"""

    pass


Segment = (
    SegmentTag
    | SegmentWildCardSingle
    | SegmentWildCardPath
    | SegmentWildCardBounded
    | SegmentNull
)


@dataclass
class TagPath:
    segments: list[Segment]


@dataclass
class QP_And:
    operands: list["QueryPlan"]


@dataclass
class QP_Or:
    operands: list["QueryPlan"]


@dataclass
class QP_Xor:
    operands: list["QueryPlan"]


@dataclass
class QP_OnlyOne:
    operands: list["QueryPlan"]


@dataclass
class QP_Not:
    operand: "QueryPlan"


QueryPlan = QP_And | QP_Or | QP_Xor | QP_OnlyOne | QP_Not | TagPath


def to_query_plan(node: Expr, prefix: list[Segment] | None = None) -> QueryPlan:
    prefix = prefix or []
    match node:
        case Tag(name, None):
            return TagPath(prefix + [SegmentTag(name)])

        case Tag(name, children):
            return to_query_plan(children, prefix + [SegmentTag(name)])

        case WildcardSingle(None):
            return TagPath(prefix + [SegmentWildCardSingle()])

        case WildcardSingle(children):
            return to_query_plan(children, prefix + [SegmentWildCardSingle()])

        case WildcardPath(None):
            return TagPath(prefix + [SegmentWildCardPath()])

        case WildcardPath(children):
            return to_query_plan(children, prefix + [SegmentWildCardPath()])

        case WildcardBounded(max_depth):
            return TagPath(prefix + [SegmentWildCardBounded(max_depth)])

        case WildcardBounded(max_depth, children):
            return to_query_plan(children, prefix + [SegmentWildCardBounded(max_depth)])

        case Null(None):
            return TagPath(prefix + [SegmentNull()])

        case Null(children):
            return to_query_plan(children, prefix + [SegmentNull()])

        case Or(operands):
            return QP_Or([to_query_plan(op, prefix) for op in operands])

        case And(operands):
            return QP_And([to_query_plan(op, prefix) for op in operands])

        case Xor(operands):
            return QP_Xor([to_query_plan(op, prefix) for op in operands])

        case OnlyOne(operands):
            return QP_OnlyOne([to_query_plan(op, prefix) for op in operands])

        case Not(operand):
            inner = to_query_plan(operand, prefix)
            if prefix:
                # a[!b] == a,!a[b]
                return QP_And([TagPath(prefix), QP_Not(inner)])

            return QP_Not(inner)


def simplify(qp: QueryPlan) -> QueryPlan:
    match qp:
        case TagPath():
            # base case, nothing to simplify
            return qp

        case QP_Not(QP_Not(inner)):
            # double negation
            return simplify(inner)

        case QP_Not(operand):
            return QP_Not(simplify(operand))

        case QP_And(operands):
            # simplify children
            simplified = map(simplify, operands)

            # flatten nested: AND(AND(a,b), c) -> AND(a,b,c)
            flattened = []
            for op in simplified:
                if isinstance(op, QP_And):
                    flattened.extend(op.operands)
                else:
                    flattened.append(op)

            # unwrap single: AND(a) -> a
            if len(flattened) == 1:
                return flattened[0]

            return QP_And(flattened)

        case QP_Or(operands):
            # simplify children
            simplified = map(simplify, operands)

            # flatten nested: OR(OR(a,b), c) -> OR(a,b,c)
            flattened = []
            for op in simplified:
                if isinstance(op, QP_Or):
                    flattened.extend(op.operands)
                else:
                    flattened.append(op)

            # unwrap single: OR(a) -> a
            if len(flattened) == 1:
                return flattened[0]

            return QP_Or(flattened)

        case QP_Xor(operands):
            simplified = list(map(simplify, operands))

            # unwrap single: XOR(a) -> a
            if len(simplified) == 1:
                return simplified[0]

            return QP_Xor(simplified)

        case QP_OnlyOne(operands):
            simplified = list(map(simplify, operands))

            # unwrap single: OnlyOne(a) -> a
            if len(simplified) == 1:
                return simplified[0]

            return QP_OnlyOne(simplified)

        case _:
            raise ValueError(f"Unknown: {type(qp)}")


if __name__ == "__main__":
    p = parser.parse
    t = Transformer().transform
    import sys

    x = sys.argv[1]

    ast = t(p(x))
    print(ast)

    qp = to_query_plan(ast)
    print(qp)

    simplified = simplify(qp)
    print(simplified)
