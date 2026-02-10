from dataclasses import dataclass

from tagumori.query.ast import (
    And,
    Expr,
    Not,
    Null,
    OnlyOne,
    Or,
    Tag,
    WildcardBounded,
    WildcardPath,
    WildcardSingle,
    Xor,
)


@dataclass
class SegmentTag:
    name: str
    is_root: bool = False
    is_leaf: bool = False


@dataclass
class SegmentWildCardSingle:
    """Matches any single tag (*)"""

    is_root: bool = False
    is_leaf: bool = False


@dataclass
class SegmentWildCardPath:
    """Matches zore or more tags (**)"""

    pass


@dataclass
class SegmentWildCardBounded:
    """Matches up to n tags (*n*)"""

    max_depth: int


Segment = (
    SegmentTag | SegmentWildCardSingle | SegmentWildCardPath | SegmentWildCardBounded
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


def to_query_plan(
    node: Expr, prefix: list[Segment] | None = None, is_root: bool = False
) -> QueryPlan:
    prefix = prefix or []
    match node:
        case Tag(name, None):
            return TagPath(prefix + [SegmentTag(name, is_root=is_root)])

        case Tag(name, children):
            is_leaf = isinstance(children, Null)
            seg = SegmentTag(name, is_root=is_root, is_leaf=is_leaf)

            if is_leaf:
                # if ~ encountered in children, terminate recursion
                # (this means that a[~[z]] is just a[~] and kind of fails silently)
                return TagPath(prefix + [seg])

            return to_query_plan(children, prefix + [seg])

        case WildcardSingle(None):
            return TagPath(prefix + [SegmentWildCardSingle()])

        case WildcardSingle(children):
            is_leaf = isinstance(children, Null)
            seg = SegmentWildCardSingle(is_root=is_root, is_leaf=is_leaf)

            if is_leaf:
                # see case Tag(name, children)
                return TagPath(prefix + [seg])

            return to_query_plan(children, prefix + [seg])

        case WildcardPath():
            raise NotImplementedError(
                "** (path wildcard) is not yet supported in queries"
            )

        case WildcardBounded():
            raise NotImplementedError(
                "*n* (bounded wildcard) is not yet supported in queries"
            )

        case Null(None):
            # ~ alone: any root-level leaf
            return TagPath(prefix + [SegmentWildCardSingle(is_root=True, is_leaf=True)])

        case Null(children):
            # ~[X]: X must be a root
            return to_query_plan(children, prefix, is_root=True)

        case Or(operands):
            return QP_Or([to_query_plan(op, prefix, is_root) for op in operands])

        case And(operands):
            return QP_And([to_query_plan(op, prefix, is_root) for op in operands])

        case Xor(operands):
            return QP_Xor([to_query_plan(op, prefix, is_root) for op in operands])

        case OnlyOne(operands):
            return QP_OnlyOne([to_query_plan(op, prefix, is_root) for op in operands])

        case Not(operand):
            inner = to_query_plan(operand, prefix, is_root)
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
