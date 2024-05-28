from collections import defaultdict
from itertools import chain
from pathlib import Path
from typing import Set, List, Optional
import json
import click

flatten = chain.from_iterable


class Vault:
    def __init__(self, filename: str):
        self.filename = filename

        with open(filename, "r") as f:
            converted_sets = {k: set(v) for k, v in json.load(f).items()}
            self.data = defaultdict(set, converted_sets)

    def files(self, tags: Optional[List[Set[str]]] = None) -> List[str]:
        return [
            file
            for file, f_tags in self.data.items()
            if any(t.issubset(f_tags) for t in tags or []) or not tags
        ]

    def tags(self) -> List[str]:
        return sorted(set(flatten(self.data.values())))

    def items(self):
        return self.data.items()

    def add_tags(self, file: str, tags: Set[str]):
        self.data[file] |= tags

    def remove_tags(self, file: str, tags: Set[str]):
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


class DelimitedSet(click.ParamType):
    name = "delimited set"

    def __init__(self, *args, delimiter=",", **kwargs):
        super().__init__(*args, **kwargs)
        self.delimiter = delimiter

    def convert(self, value, param, ctx):
        if isinstance(value, set):
            return True

        try:
            return {elem.strip() for elem in value.split(self.delimiter)}

        except ValueError:
            self.fail(
                f"Couldn't parse set from {value} with delimiter {self.delimiter}",
                param,
                ctx,
            )


@click.group()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.pass_context
def cli(ctx, vault: Path):
    ctx.obj = ctx.with_resource(Vault(vault))


@cli.command()
@click.argument("vaultname")
def init_vault(vaultname: str):
    Vault.init(vaultname)


@cli.command()
@click.pass_obj
@click.option("-t", "tags", type=DelimitedSet())
@click.option("-f", "filename", type=click.Path(exists=True), multiple=True)
@click.option("-r", "read", type=click.File("r"), help="Read file or stdin (-r -)")
def add_tag(vault: Vault, filename: List[Path], tags: Set[str], read: str):
    filenames = filename or []
    if read:
        filenames.extend(read.read().strip().split("\n"))

    for fn in filenames:
        vault.add_tags(fn, tags)


@cli.command()
@click.pass_obj
@click.option("-t", "tags", type=DelimitedSet())
@click.option("-f", "filename", type=click.Path(exists=True), multiple=True)
def remove_tag(vault: Vault, filename: List[Path], tags: Set[str]):
    for fn in filename:
        vault.remove_tags(fn, tags)


@cli.command()
@click.pass_obj
@click.option(
    "-t",
    "tags",
    type=DelimitedSet(),
    multiple=True,
    help="Each instance of -t is considered an AND condition, which is then OR'd with others",
)
def ls(vault: Vault, tags: List[Set[str]]):
    for file in vault.files(tags):
        click.echo(file)


@cli.command()
@click.pass_obj
def list_tags(vault: Vault):
    for tag in vault.tags():
        click.echo(tag)


if __name__ == "__main__":
    cli()
