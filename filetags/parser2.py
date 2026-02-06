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


# Query plan stuff
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

        case WildcardPath(None):
            return TagPath(prefix + [SegmentWildCardPath(is_root=is_root)])

        case WildcardPath(children):
            return to_query_plan(children, prefix + [SegmentWildCardPath()])

        case WildcardBounded(max_depth):
            return TagPath(prefix + [SegmentWildCardBounded(max_depth)])

        case WildcardBounded(max_depth, children):
            return to_query_plan(children, prefix + [SegmentWildCardBounded(max_depth)])

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


import sqlite3  # noqa
from itertools import chain  # noqa
from filetags import crud  # noqa
from functools import reduce, partial  # noqa
from collections import Counter  # noqa

flatten = chain.from_iterable


def _build_value(segment: Segment):
    """Returns pairs of (name, is_any)"""
    match segment:
        case SegmentTag(name, is_root, is_leaf):
            return (name, 0, is_root, is_leaf)
        case SegmentWildCardSingle(is_root, is_leaf):
            return (None, 1, is_root, is_leaf)


def find_all(conn, path: TagPath, case):
    values_ph = ", ".join("(?,?,?,?,?)" for _ in path)

    # build values
    rows = ((i, *vals) for i, vals in enumerate(map(_build_value, path), 1))
    values = tuple(flatten(rows))

    # configure case sensitivity
    collate_clause = "" if case else "COLLATE NOCASE"

    q = f"""
        WITH path(depth, tag_name, is_any, is_root, is_leaf) AS (
            VALUES {values_ph}
        ),

        match(file_id, id, depth) AS (
            SELECT
                file_tag.file_id,
                file_tag.id,
                1
            FROM file_tag
            JOIN tag ON tag.id = file_tag.tag_id
            JOIN path
                ON path.depth = 1
                AND (
                    path.tag_name = tag.name {collate_clause}
                    OR
                    path.is_any = 1 --wilcard (*) 
                )
                AND (
                    -- root check
                    path.is_root = 0
                    OR
                    file_tag.parent_id IS NULL
                )

            UNION ALL

            SELECT
                child.file_id,
                child.id,
                parent.depth + 1
            FROM match parent
            JOIN file_tag child
                ON child.parent_id = parent.id
                AND child.file_id = parent.file_id
            JOIN tag ON child.tag_id = tag.id
            JOIN path
                ON path.depth = parent.depth + 1
                AND (
                    path.tag_name = tag.name {collate_clause}
                    OR
                    path.is_any = 1 --wilcard (*) 
                )
        )

        SELECT DISTINCT file_id FROM match 
        WHERE depth = (SELECT MAX(depth) FROM path)
    """
    return {x["file_id"] for x in conn.execute(q, values).fetchall()}


# missing: wilcard handling, recursive matches (** & *n*), case insensitive
def execute(conn: sqlite3.Connection, qp: QueryPlan, case: bool = True):
    # partial for keeping calls simpler
    _exec = partial(execute, conn, case=case)
    match qp:
        case TagPath(segments):
            return find_all(conn, segments, case)

        case QP_And(operands):
            # short circuit if any set is empty
            first, *rest = operands
            result = _exec(first)
            for op in rest:
                if not result:
                    return set()
                result &= _exec(op)
            return result

        case QP_Or(operands):
            # short circuit technically possible, but would require identifying
            # when "all" records were returned
            return set.union(*(_exec(op) for op in operands))

        case QP_Xor(operands):
            return reduce(lambda a, b: a ^ b, (_exec(op) for op in operands))

        case QP_OnlyOne(operands):
            c = Counter(flatten(_exec(op) for op in operands))
            return {x for x, count in c.items() if count == 1}

        case QP_Not(operand):
            return NotImplemented


if __name__ == "__main__":
    p = parser.parse
    t = Transformer().transform
    import sys

    x = sys.argv[1]

    if len(sys.argv) > 2:
        case = bool(int(sys.argv[2]))
    else:
        case = True

    ast = t(p(x))
    print(ast)

    print("Valid for storage:", validate_for_storage(ast))

    qp = to_query_plan(ast)
    print(qp)

    simplified = simplify(qp)
    print(simplified)

    with sqlite3.connect("vault.db") as conn:
        conn.row_factory = sqlite3.Row
        # conn.set_trace_callback(print)
        res = execute(conn, simplified, case)
        files = crud.file.get_many(conn, list(res))

    print(res)
    for f in files:
        print(f["path"])
