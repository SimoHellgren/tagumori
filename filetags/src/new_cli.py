from pathlib import Path
import json
import shutil
from tempfile import NamedTemporaryFile
import click
from filetags.src.models.vault import Vault
from filetags.src.parser import parse


@click.group()
@click.option("--vault", type=click.Path(), default="./vault.json")
@click.pass_context
def cli(ctx, vault: Path):
    if not Path(vault).exists():
        vault_obj = Vault([])

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
@click.option("-t", "tag", is_flag=True)
@click.option("-s", "select", default="")
@click.option("-e", "exclude", default="")
@click.pass_obj
def ls(vault: Vault, tag: bool, select: str, exclude: str):
    select_node = parse(select)
    exclude_node = parse(exclude)

    for file, tags in vault.entries():
        # skip if all excludes match
        if exclude and all(n.is_subtree(file) for n in exclude_node.children):
            continue

        # skip if includes don't match
        if select and not all(n.is_subtree(file) for n in select_node.children):
            continue

        tagstring = f"\t[{','.join(str(t) for t in tags)}]" if tag else ""
        click.echo(
            click.style(f"{file.value}", fg="green") + click.style(tagstring, fg="blue")
        )


@cli.command()
@click.pass_obj
@click.argument("filename", nargs=-1)
def show(vault: Vault, filename: str):

    for f in filename:
        file = vault.find(lambda x: x.value == f)

        if file:
            tagstring = f"\t[{','.join(str(t) for t in file.children)}]"
            click.echo(
                click.style(f"{file.value}", fg="green")
                + click.style(tagstring, fg="blue")
            )


@cli.group()
@click.pass_obj
def tag(vault: Vault):
    pass


@tag.command(name="ls")
@click.pass_obj
def list_tags(vault: Vault):
    for tag in sorted(vault.tags()):
        click.echo(tag)
