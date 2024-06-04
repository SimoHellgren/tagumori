from pathlib import Path
from typing import Set, List
from collections import defaultdict
from tempfile import NamedTemporaryFile
import shutil
import json
import click

from filetags.src.models import Vault, DelimitedSet


@click.group()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.pass_context
def cli(ctx, vault: Path):
    if not Path(vault).exists():
        vault_obj = Vault(defaultdict(set), set())

    else:
        with open(vault) as f:
            data = json.load(f)
            vault_obj = Vault.from_json(data)

    ctx.obj = vault_obj

    @ctx.call_on_close
    def save():
        # write to temporary file for safety
        # because python<3.12, need to work around the tmpfile
        # getting deleted before we can use it to replace the actual one

        json_data = vault_obj.to_json(indent=2)
        with NamedTemporaryFile(
            "w", prefix="vault_", suffix=".json", dir=".", delete=False
        ) as f:
            f.write(json_data)

        shutil.copyfile(f.name, vault)
        Path(f.name).unlink()


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
    "-s",
    "select",
    type=DelimitedSet(),
    multiple=True,
    help="Each instance of `select` is considered an AND condition, which is then OR'd with others",
)
@click.option(
    "-e",
    "exclude",
    type=DelimitedSet(),
    multiple=True,
    help="Each instance of `exclude` is considered an AND condition, which is then OR'd with others",
)
def ls(vault: Vault, select: List[Set[str]], exclude: List[Set[str]]):
    for file in vault.files(select, exclude):
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


@tag.command()
@click.option("-t", "tag", type=click.STRING, required=True)
@click.option("--tag-along", type=DelimitedSet())
@click.pass_obj
def add_tag_along(vault: Vault, tag: str, tag_along: Set[str]):
    vault.add_tagalongs(tag, tag_along)


if __name__ == "__main__":
    cli()
