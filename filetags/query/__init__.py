from sqlite3 import Connection

from filetags.query.ast import Expr, Transformer, validate_for_storage
from filetags.query.executor import execute
from filetags.query.parser import Lark_StandAlone
from filetags.query.planner import simplify, to_query_plan


def _string_to_ast(string: str) -> Expr:
    parser = Lark_StandAlone(transformer=Transformer())
    ast = parser.parse(string)
    return ast


def search(conn: Connection, string: str, case: bool = True) -> set[int]:
    ast = _string_to_ast(string)
    query_plan = simplify(to_query_plan(ast))
    return execute(conn, query_plan, case)


def parse_for_storage(string) -> Expr:
    ast = _string_to_ast(string)

    if not validate_for_storage(ast):
        raise ValueError(
            "Only AND and actual tags (no wildcards) are allowed for storage."
        )

    return ast
