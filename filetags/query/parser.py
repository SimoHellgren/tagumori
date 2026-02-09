"""Generates parser from grammar.

Will be replaced with a standalone parser eventually.
"""

from pathlib import Path

import lark

GRAMMAR = Path(__file__).parent / "grammar.lark"

parser = lark.Lark(GRAMMAR.read_text(), parser="lalr")
