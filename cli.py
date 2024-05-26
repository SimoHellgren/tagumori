from collections import defaultdict
import json
import click

# a vault is a mapping of filenames to tags
Vault = defaultdict[str, set[str]]


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
    with open(vaultname, "w") as f:
        json.dump({}, f, indent=2)


def parse_tags(tags):
    return {tag.strip() for tag in tags.split(",")}


@cli.command()
@click.argument("vault", type=click.Path())
@click.argument("filename", type=click.Path())
@click.argument("tags", type=click.STRING)
def add_tag(vault, filename, tags):

    vault_ = load_vault(vault)

    vault_[filename] |= parse_tags(tags)

    print(vault_)

    save_vault(vault, vault_)


@cli.command()
@click.argument("vault", type=click.Path())
@click.argument("tags", type=click.STRING)
def ls(vault, tags):
    vault_ = load_vault(vault)
    criteria = parse_tags(tags)

    for file, tags_ in vault_.items():
        if criteria.issubset(tags_):
            click.echo(file)


if __name__ == "__main__":
    cli()
