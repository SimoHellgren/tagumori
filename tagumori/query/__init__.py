from collections.abc import Callable
from sqlite3 import Connection

from tagumori.query.ast import Expr, Transformer, validate_for_storage
from tagumori.query.executor import execute
from tagumori.query.parser import Lark_StandAlone
from tagumori.query.planner import simplify, to_query_plan


def _string_to_ast(string: str) -> Expr:
    parser = Lark_StandAlone(transformer=Transformer())
    ast = parser.parse(string)
    return ast


def search(
    conn: Connection,
    string: str,
    get_all_ids: Callable[[], set[int]],
    case: bool = True,
) -> set[int]:
    ast = _string_to_ast(string)
    query_plan = simplify(to_query_plan(ast))
    return execute(conn, query_plan, get_all_ids, case)


def parse_for_storage(string: str) -> Expr:
    ast = _string_to_ast(string)

    if not validate_for_storage(ast):
        raise ValueError(
            "Only AND and actual tags (no wildcards) are allowed for storage."
        )

    return ast
