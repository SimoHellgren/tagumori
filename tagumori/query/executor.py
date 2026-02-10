import sqlite3
from collections import Counter
from functools import cache, reduce
from itertools import chain

from tagumori import crud
from tagumori.query.planner import (
    QP_And,
    QP_Not,
    QP_OnlyOne,
    QP_Or,
    QP_Xor,
    QueryPlan,
    Segment,
    SegmentTag,
    SegmentWildCardSingle,
    TagPath,
)

flatten = chain.from_iterable


def _build_value(segment: Segment):
    """Returns tuples of (name, is_any, is_root, is_leaf)"""
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

        SELECT DISTINCT match.file_id FROM match
        JOIN path ON path.depth = match.depth
        WHERE match.depth = (SELECT MAX(depth) FROM path)
        AND (
            path.is_leaf = 0
            OR
            NOT EXISTS (SELECT 1 FROM file_tag WHERE file_tag.parent_id = match.id)
        )
    """
    return {x["file_id"] for x in conn.execute(q, values).fetchall()}


def execute(conn: sqlite3.Connection, qp: QueryPlan, case: bool = True):
    # cached func for use with NOT
    @cache
    def get_all_file_ids():
        return {x["id"] for x in crud.file.get_all(conn)}

    def _exec(qp: QueryPlan):
        """Inner function to simplify calling and caching"""

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
                return get_all_file_ids() - _exec(operand)

    return _exec(qp)
