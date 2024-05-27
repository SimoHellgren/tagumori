from collections import defaultdict
from itertools import chain
from pathlib import Path
import json
import click

flatten = chain.from_iterable

# a vault is a mapping of filenames to tags
# Vault = defaultdict[str, set[str]]


def load_vault(filename):
    with open(filename, "r") as f:
        converted_sets = {k: set(v) for k, v in json.load(f).items()}
        return defaultdict(set, converted_sets)


def save_vault(filename, data):
    with open(filename, "w") as f:
        # default handles conversion of sets to lists.
        # possibly need to do something more elegant later.
        json.dump(data, f, indent=2, default=list)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("vaultname")
def init_vault(vaultname):
    path = Path(vaultname)

    if path.exists():
        click.echo(f"{vaultname} already exists.")

    else:
        with open(path, "w") as f:
            json.dump({}, f, indent=2)


def parse_tags(tags):
    return {tag.strip() for tag in tags.split(",")}


@cli.command()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.option("-t", "tags", type=click.STRING)
@click.option("-f", "filename", type=click.Path(exists=True), multiple=True)
@click.option("-r", "read", type=click.File("r"), help="Read file or stdin (-r -)")
def add_tag(vault, filename, tags, read):

    vault_ = load_vault(vault)

    filenames = filename or []
    if read:
        filenames.extend(read.read().strip().split("\n"))

    for fn in filenames:
        vault_[fn] |= parse_tags(tags)

    save_vault(vault, vault_)


@cli.command()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.option("-t", "tags", type=click.STRING)
@click.option("-f", "filename", type=click.Path(exists=True), multiple=True)
def remove_tag(vault, filename, tags):

    vault_ = load_vault(vault)

    for fn in filename:
        vault_[fn] -= parse_tags(tags)

    save_vault(vault, vault_)


@cli.command()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.option(
    "-t",
    "tags",
    type=click.STRING,
    multiple=True,
    help="Each instance of -t is considered an AND condition, which is then OR'd with others",
)
def ls(vault, tags):
    vault_ = load_vault(vault)

    tag_groups = [parse_tags(ts) for ts in tags]

    for file, tags_ in vault_.items():
        # one of the tag groups must be found, or no tags were provided
        if any(t.issubset(tags_) for t in tag_groups) or not tag_groups:
            click.echo(file)


@cli.command()
@click.option("--vault", type=click.Path(), default="./vault.json")
def list_tags(vault):
    vault_ = load_vault(vault)

    all_tags = set(flatten(vault_.values()))

    for tag in sorted(all_tags):
        click.echo(tag)


if __name__ == "__main__":
    cli()
