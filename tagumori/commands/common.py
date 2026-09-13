"""Module for common resources, such as cli option groups."""

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
