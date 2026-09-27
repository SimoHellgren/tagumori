def not_none[T](value: T | None) -> T:
    """Makes mypy happy when doing e.g:
    tag = crud.tag.create(...) # Tag | None
    tag.id # not checking for None!
    """
    assert value is not None
    return value
