from pathlib import Path
from typing import Set, List
import click

from filetags.src.models import Vault, DelimitedSet


@click.group()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.pass_context
def cli(ctx, vault: Path):
    if not Path(vault).exists():
        Vault.init(vault)

    ctx.obj = ctx.with_resource(Vault(vault))


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
    for tag in vault.tags:
        click.echo(tag)


@cli.group()
@click.pass_obj
def tag(vault):
    pass


@tag.command()
@click.option("-t", "tag", type=click.STRING, required=True)
@click.option("--tag-along", type=DelimitedSet())
@click.pass_obj
def create(vault: Vault, tag: str, tag_along):
    vault.create_tag(tag, tag_along)


if __name__ == "__main__":
    cli()
