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

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def key(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

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
def add_tag(vault, filename, tags, read):
    filenames = filename or []
    if read:
        filenames.extend(read.read().strip().split("\n"))

    for fn in filenames:
        vault[fn] |= parse_tags(tags)


@cli.command()
@click.pass_obj
@click.option("-t", "tags", type=click.STRING)
@click.option("-f", "filename", type=click.Path(exists=True), multiple=True)
def remove_tag(vault, filename, tags):
    for fn in filename:
        vault[fn] -= parse_tags(tags)


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

    for file, tags_ in vault.items():
        # one of the tag groups must be found, or no tags were provided
        if any(t.issubset(tags_) for t in tag_groups) or not tag_groups:
            click.echo(file)


@cli.command()
@click.pass_obj
def list_tags(vault):

    all_tags = set(flatten(vault.values()))

    for tag in sorted(all_tags):
        click.echo(tag)


if __name__ == "__main__":
    cli()
