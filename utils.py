from itertools import chain

flatten = chain.from_iterable
find = lambda f, it, d=None: next(filter(f, it), d)
