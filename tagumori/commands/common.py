"""Module for common resources, such as cli option groups."""

from pathlib import Path

import click

from tagumori.query import _string_to_ast
from tagumori.query.ast import Expr, Not, or_, validate_for_storage


class TagQuery(click.ParamType):
    name = "tag query"

    def convert(self, value, param, ctx):

        return _string_to_ast(value)


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


def select_callback(ctx, param, value) -> Expr | None:
    """Wraps multiple instances of tag queries in and OR node."""
    return or_(*value)


def exclude_callback(ctx, param, value) -> Expr | None:
    """Wraps multiple instances of tag queries in and OR node."""
    return or_(*map(Not, value))


def query_options(func):
    func = click.option(
        "-s", "--select", multiple=True, type=TagQuery(), callback=select_callback
    )(func)
    func = click.option(
        "-e",
        "--exclude",
        multiple=True,
        type=TagQuery(),
        callback=exclude_callback,
    )(func)
    func = click.option(
        "-I", "--ignore-tag-case", is_flag=True, help="Ignore tag case."
    )(func)

    return func


def regex_options(func):
    func = click.option(
        "-p", "--pattern", help="Filter output by regex pattern.", default=r".*"
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
