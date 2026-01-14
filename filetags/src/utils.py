import re
from itertools import chain, islice
from typing import Iterator

flatten = chain.from_iterable
find = lambda f, it, d=None: next(filter(f, it), d)


def drop(it: Iterator, n: int):
    return islice(it, n, None)


def tail(it: Iterator):
    return drop(it, 1)


def compile_pattern(pattern: str, ignore_case: bool):
    if not pattern:
        return None

    flags = re.IGNORECASE if ignore_case else 0

    return re.compile(pattern, flags)
