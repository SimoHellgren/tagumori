from collections import Counter
from pathlib import Path
import json
import shutil
from tempfile import NamedTemporaryFile
import click
from filetags.src.models.vault import Vault
from filetags.src.parser import parse
from filetags.src.utils import flatten, drop


@click.group()
@click.option(
    "--vault", type=click.Path(), default="./vault.json", help="Defaults to vault.json"
)
@click.pass_context
def cli(ctx, vault: Path):
    if not Path(vault).exists():
        vault_obj = Vault([], [])

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


@cli.command(help="List files (with optional filters)")
@click.option("-t", "tag", is_flag=True)
@click.option("-s", "select", multiple=True)
@click.option("-e", "exclude", multiple=True)
@click.pass_obj
def ls(vault: Vault, tag: bool, select: str, exclude: str):
    # Having to specify children here is a touch clunky.
    # Could just have parse return a list instead - will consider.
    select_nodes = [parse(s).children for s in select]
    exclude_nodes = [parse(e).children for e in exclude]

    for file, tags in vault.filter(select_nodes, exclude_nodes):
        tagstring = f"\t[{','.join(str(t) for t in tags)}]" if tag else ""
        click.echo(
            click.style(f"{file.value}", fg="green") + click.style(tagstring, fg="blue")
        )


@cli.command(help="Show details of one or more files")
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


@cli.command(help="Add tags to files")
@click.pass_obj
@click.option(
    "-f", "filename", required=True, type=click.Path(exists=True), multiple=True
)
@click.option("-t", "tag", required=True, type=click.STRING, multiple=True)
def add(vault: Vault, filename: list[Path], tag: list[str]):
    for file in filename:
        nodes = [parse(t, file) for t in tag]
        first, *rest = nodes
        for node in rest:
            first.merge(node)

        vault.add_tag(first)


@cli.command(help="Remove tags from files")
@click.pass_obj
@click.option(
    "-f", "filename", required=True, type=click.Path(exists=True), multiple=True
)
@click.option("-t", "tag", required=True, type=click.STRING, multiple=True)
def remove(vault: Vault, filename: list[Path], tag: list[str]):
    for file in filename:
        for t in tag:
            node = parse(t, file)
            vault.remove_tag(node)


@cli.group(help="Tag management")
@click.pass_obj
def tag(vault: Vault):
    pass


@tag.command(name="ls", help="List all tags")
@click.pass_obj
def list_tags(vault: Vault):
    for tag in sorted(vault.tags()):
        click.echo(tag)


@tag.command(name="rename", help="Rename a tag")
@click.pass_obj
@click.argument("old")
@click.argument("new")
def rename_tag(vault: Vault, old: str, new: str):
    vault.rename_tag(old, new)


@tag.command(name="stats")
@click.option("-s", "skip", type=click.INT, default=0)
@click.option("-l", "limit", type=click.INT, default=-1)
@click.pass_obj
def tag_stats(vault: Vault, skip: int, limit: int):
    counts = Counter(
        flatten((t.value for t in file.descendants()) for file, _ in vault.entries())
    )

    if limit < 0:
        limit = None
    else:
        limit = limit + skip

    for tag, count in drop(counts.most_common(limit), skip):
        click.echo(f"{tag}: {count}")


@cli.group(help="Tagalong management")
@click.pass_obj
def tagalong(vault: Vault):
    pass


@tagalong.command(name="ls")
@click.pass_obj
def list_tagalongs(vault: Vault):
    for a, b in sorted(vault.tagalongs):
        click.echo(f"{a} -> {b}")


@tagalong.command(name="add")
@click.pass_obj
@click.option("-t", "tag", multiple=True)
@click.option("-ta", "tagalong", multiple=True)
def add_tagalong(vault: Vault, tag: str, tagalong: str):
    for x in tag:
        for y in tagalong:
            vault.add_tagalong(x, y)


@tagalong.command(name="remove")
@click.pass_obj
@click.option("-t", "tag", multiple=True)
@click.option("-ta", "tagalong", multiple=True)
def remove_tagalong(vault: Vault, tag: str, tagalong: str):
    for x in tag:
        for y in tagalong:
            vault.remove_tagalong(x, y)
