from collections import defaultdict
from itertools import chain
from pathlib import Path
import json
import click

flatten = chain.from_iterable


class Vault:
    def __init__(self, filename):
        self.filename = filename

        with open(filename, "r") as f:
            converted_sets = {k: set(v) for k, v in json.load(f).items()}
            self.data = defaultdict(set, converted_sets)

    def files(self, tags=None):
        """Lists files, by filtering by tags.

        Type of tags is list[set].
        """
        return [
            file
            for file, f_tags in self.data.items()
            if any(t.issubset(f_tags) for t in tags) or not tags
        ]

    def tags(self):
        return sorted(set(flatten(self.data.values())))

    def add_tags(self, file, tags):
        self.data[file] |= tags

    def remove_tags(self, file, tags):
        self.data[file] -= tags

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, trace):
        # only write if no exception
        if exc_type is None:
            with open(self.filename, "w") as f:
                # default handles conversion of sets to lists.
                # possibly need to do something more elegant later.
                json.dump(self.data, f, indent=2, default=list)

    @staticmethod
    def init(name):
        path = Path(name)

        if path.exists():
            click.echo(f"{name} already exists.")

        else:
            with open(path, "w") as f:
                json.dump({}, f, indent=2)


@click.group()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.pass_context
def cli(ctx, vault):
    ctx.obj = ctx.with_resource(Vault(vault))


@cli.command()
@click.argument("vaultname")
def init_vault(vaultname):
    Vault.init(vaultname)


def parse_tags(tags):
    if not tags:
        return set()

    return {tag.strip() for tag in tags.split(",")}


@cli.command()
@click.pass_obj
@click.option("-t", "tags", type=click.STRING)
@click.option("-f", "filename", type=click.Path(exists=True), multiple=True)
@click.option("-r", "read", type=click.File("r"), help="Read file or stdin (-r -)")
def add_tag(vault: Vault, filename, tags, read):
    filenames = filename or []
    if read:
        filenames.extend(read.read().strip().split("\n"))

    for fn in filenames:
        vault.add_tags(fn, parse_tags(tags))


@cli.command()
@click.pass_obj
@click.option("-t", "tags", type=click.STRING)
@click.option("-f", "filename", type=click.Path(exists=True), multiple=True)
def remove_tag(vault: Vault, filename, tags):
    for fn in filename:
        vault.remove_tags(fn, parse_tags(tags))


@cli.command()
@click.pass_obj
@click.option(
    "-t",
    "tags",
    type=click.STRING,
    multiple=True,
    help="Each instance of -t is considered an AND condition, which is then OR'd with others",
)
def ls(vault, tags):
    tag_groups = [parse_tags(ts) for ts in tags]

    for file in vault.files(tag_groups):
        click.echo(file)


@cli.command()
@click.pass_obj
def list_tags(vault):
    for tag in vault.tags():
        click.echo(tag)


if __name__ == "__main__":
    cli()
