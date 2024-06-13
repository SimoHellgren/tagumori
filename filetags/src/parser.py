import lark
from filetags.src.models.node import Node

# grammar for parsing expressions like A[a,b],B[b] into nodes
#
GRAMMAR = """
root: list |

tag: NAME [ list ]
list: "[" [ tag ("," tag)*  ] "]" | tag ("," tag)* 

NAME: WORD | STRING
WORD: (LETTER | DIGIT | "_" | "-")+

%import common.LETTER
%import common.DIGIT
%import common.ESCAPED_STRING -> STRING
%import common.WS
%ignore WS
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
    NAME = lambda s, n: n.value


parser = lark.Lark(GRAMMAR, start="root")
transformer = Transformer()


def parse(s: str) -> Node:
    tree = parser.parse(s)
    return transformer.transform(tree)


if __name__ == "__main__":
    a = parse("x")
    print(a)

    b = parse("x[a]")
    print(b)

    c = parse("x,y")
    print(c)
