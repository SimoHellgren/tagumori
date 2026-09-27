import re
from collections.abc import Callable
from itertools import chain

flatten = chain.from_iterable


def compile_matcher(
    pattern: str, ignore_case: bool, invert_match: bool
) -> Callable[[str], bool]:

    flags = re.IGNORECASE if ignore_case else 0

    return lambda x: (
        bool(re.search(string=x, pattern=pattern, flags=flags)) ^ invert_match
    )
