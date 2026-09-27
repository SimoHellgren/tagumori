"""Module for common resources, such as cli option groups."""

import re
from pathlib import Path

import click

from tagumori.query import parse
from tagumori.query.ast import Expr, and_, or_, validate_for_storage


class TagQuery(click.ParamType):
    name = "tag query"

    def convert(self, value, param, ctx):

        return parse(value)


class TagTree(TagQuery):
    name = "tag tree"

    def convert(self, value, param, ctx):

        parsed = super().convert(value, param, ctx)

        if not validate_for_storage(parsed):
            self.fail(
                "Only AND and actual tags (no wildcards) are allowed for storage.",
                param,
                ctx,
            )

        return parsed


def tag_tree_callback(ctx, param, value) -> Expr:
    result = and_(*value)

    # -t is required, meaning result is never None.
    # This assert is here to make mypy happy
    assert result is not None

    return result


def query_callback(ctx, param, value) -> Expr | None:
    """Wraps multiple instances of tag queries in and OR node."""
    return or_(*value)


def query_options(func):
    func = click.option(
        "-s", "--select", multiple=True, type=TagQuery(), callback=query_callback
    )(func)
    func = click.option(
        "-e",
        "--exclude",
        multiple=True,
        type=TagQuery(),
        callback=query_callback,
    )(func)
    func = click.option(
        "-I", "--ignore-tag-case", is_flag=True, help="Ignore tag case."
    )(func)

    return func


def validate_regex(ctx, param, value):
    try:
        re.compile(value)
    except re.error as e:
        raise click.BadParameter(f"Invalid regex: {e}") from e
    return value


def regex_options(func):
    func = click.option(
        "-p",
        "--pattern",
        help="Filter output by regex pattern.",
        default=r".*",
        callback=validate_regex,
    )(func)
    func = click.option("-i", "--ignore-case", is_flag=True, help="Ignore regex case.")(
        func
    )
    func = click.option(
        "-v",
        "--invert-match",
        is_flag=True,
        help="Inverts the regex match (not select/exclude).",
    )(func)
    return func


def file_print_options(func):
    func = click.option(
        "-l", "--long", type=click.BOOL, is_flag=True, help="Long listing format."
    )(func)
    func = click.option(
        "--relative-to",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=Path("."),
        help="Display paths relative to given directory.",
    )(func)
    func = click.option("--prefix", default="")(func)

    return func
