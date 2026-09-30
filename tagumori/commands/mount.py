from pathlib import Path

import click

from tagumori.commands.context import LazyVault


@click.command(help="Mounts tagumori as a FUSE")
@click.argument("path", type=click.Path(path_type=Path, file_okay=False))
@click.pass_obj
def mount(lazy_vault: LazyVault, path: Path):
    print(lazy_vault)
    click.echo(path)
