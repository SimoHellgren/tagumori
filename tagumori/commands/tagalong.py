from itertools import product
from pathlib import Path

import click

import tagumori.service
from tagumori.commands.context import LazyVault


@click.group(help="Tagalong management")
@click.pass_obj
def tagalong(lazy_vault: LazyVault):
    pass


@tagalong.command(help="Register new tagalongs.")
@click.option("-t", "--tag", required=True, multiple=True)
@click.option("-ta", "--tagalong", required=True, multiple=True)
@click.pass_obj
def add(lazy_vault: LazyVault, tag: tuple[str, ...], tagalong: tuple[str, ...]):
    with lazy_vault as vault:
        sources = vault.tags.get_or_create_many(tag)
        targets = vault.tags.get_or_create_many(tagalong)

        for source, target in product(sources, targets):
            vault.tagalongs.create(source.id, target.id)


@tagalong.command(help="Remove tagalongs.")
@click.option("-t", "--tag", required=True, multiple=True)
@click.option("-ta", "--tagalong", required=True, multiple=True)
@click.pass_obj
def remove(lazy_vault: LazyVault, tag: tuple[str, ...], tagalong: tuple[str, ...]):
    with lazy_vault as vault:
        sources = vault.tags.get_many_by_name(tag)
        targets = vault.tags.get_many_by_name(tagalong)

        for source, target in product(sources, targets):
            vault.tagalongs.delete(source.id, target.id)


@tagalong.command(help="Show all tagalongs.")
@click.pass_obj
def ls(lazy_vault: LazyVault):
    # TODO: Consider adding a grep-like filter if such would prove to be useful
    with lazy_vault as vault:
        for ta in tagumori.service.list_tagalong_names(vault):
            click.echo(f"{ta.tag_name} -> {ta.tagalong_name}")


@tagalong.command(help="Apply all tagalongs (to all files by default).")
@click.option(
    "-f", "--file", type=click.Path(path_type=Path, exists=True), multiple=True
)
@click.pass_obj
def apply(lazy_vault: LazyVault, file: tuple[Path, ...]):
    # TODO: consider filtering by tag
    with lazy_vault as vault:
        files = vault.files.get_many_by_path(file)
        file_ids = [f.id for f in files]

        vault.tagalongs.apply(file_ids)
