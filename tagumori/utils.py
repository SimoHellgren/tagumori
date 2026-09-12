import re
from itertools import chain

flatten = chain.from_iterable


def compile_pattern(pattern: str, ignore_case: bool):
    if not pattern:
        return None

    flags = re.IGNORECASE if ignore_case else 0

    return re.compile(pattern, flags)
