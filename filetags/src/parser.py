import lark
from filetags.src.models.node import Node

# grammar for parsing expressions like A[a,b],B[b] into nodes
GRAMMAR = """
root: list |

tag: name [ list ]
list: "[" [ tag ("," tag)*  ] "]" | tag ("," tag)* 

?name: WORD (" " WORD)*
WORD: (LETTER | DIGIT | "_" | "-")+

%import common.LETTER
%import common.DIGIT
%import common.WS
"""


class Transformer(lark.Transformer):
    def __init__(self, rootvalue=""):
        self.rootvalue = rootvalue

    def root(self, t):
        if not t:
            children = []
        else:
            (children,) = t

        return Node(self.rootvalue, children)

    def tag(self, s):
        value, children = s
        return Node(value, children)

    list = list
    name = lambda s, l: " ".join(l)
    WORD = lambda s, w: w.value


parser = lark.Lark(GRAMMAR, start="root")
transformer = Transformer()


def parse(s: str, rootvalue="") -> Node:
    tree = parser.parse(s)
    transformer = Transformer(rootvalue)
    return transformer.transform(tree)
