"""Module for common resources, such as cli option groups."""

from pathlib import Path

import click


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


def query_options(func):
    func = click.option("-s", "--select", multiple=True)(func)
    func = click.option("-e", "--exclude", multiple=True)(func)
    func = click.option(
        "-I", "--ignore-tag-case", is_flag=True, help="Ignore tag case."
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
