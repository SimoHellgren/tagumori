from typing import Iterator
from itertools import chain, islice

flatten = chain.from_iterable
find = lambda f, it, d=None: next(filter(f, it), d)


def drop(it: Iterator, n: int):
    return islice(it, n, None)


def tail(it: Iterator):
    return drop(it, 1)
