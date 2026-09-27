from dataclasses import dataclass

from tagumori.query.parser import Transformer as StandaloneTransformer


@dataclass
class Tag:
    name: str
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return self.name

        return f"{self.name}[{self.children}]"


@dataclass
class Xor:
    """Binary XOR - true when odd number of operands are true."""

    operands: list["Expr"]

    def __str__(self) -> str:
        return "^".join(_wrap(self, op) for op in self.operands)


@dataclass
class OnlyOne:
    """Exactly one of - true when exactly one operand is true."""

    operands: list["Expr"]

    def __str__(self) -> str:
        ops = ",".join(_wrap(self, op) for op in self.operands)
        return f"xor({ops})"


@dataclass
class And:
    operands: list["Expr"]

    def __str__(self) -> str:
        return ",".join(_wrap(self, op) for op in self.operands)


@dataclass
class Or:
    operands: list["Expr"]

    def __str__(self) -> str:
        return "|".join(_wrap(self, op) for op in self.operands)


@dataclass
class Not:
    operand: "Expr"

    def __str__(self) -> str:
        return f"!{_wrap(self, self.operand)}"


@dataclass
class Null:
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return "~"

        return f"~[{self.children}]"


@dataclass
class WildcardSingle:
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return "*"

        return f"*[{self.children}]"


@dataclass
class WildcardPath:
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return "**"

        return f"**[{self.children}]"


@dataclass
class WildcardBounded:
    max_depth: int
    children: "Expr | None" = None

    def __str__(self) -> str:
        if not self.children:
            return f"*{self.max_depth}*"

        return f"*{self.max_depth}*[{self.children}]"


def precedence(expr: "Expr") -> int:
    match expr:
        case Xor():
            return 0

        case Or():
            return 1

        case And():
            return 2

        case Not():
            return 3

        case _:
            return 4


def _wrap(parent: "Expr", operand: "Expr") -> str:
    rendered = str(operand)

    if precedence(operand) < precedence(parent):
        return f"({rendered})"

    return rendered


class Transformer(StandaloneTransformer):
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


type Expr = (
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

        # if-condition makes mypy happy (otherwise thinks it can be None)
        case Tag(_, children) if children is not None:
            return validate_for_storage(children)

        case And(operands):
            return all(map(validate_for_storage, operands))

        case _:
            return False


def and_(*operands: Expr) -> Expr | None:
    """A 'smart' constuctor for And:
    Wraps operands in And if necessary
    """
    if not operands:
        return None

    if len(operands) == 1:
        return operands[0]

    # explicit `list` for type correctness
    return And(list(operands))


def or_(*operands: Expr) -> Expr | None:
    """A 'smart' constuctor for Or:
    Wraps operands in Or if necessary
    """

    if not operands:
        return None

    if len(operands) == 1:
        return operands[0]

    # explicit `list` for type correctness
    return Or(list(operands))
