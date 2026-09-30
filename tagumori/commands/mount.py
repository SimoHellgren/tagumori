from pathlib import Path

import click

from tagumori.commands.context import LazyVault


@click.command(help="Mounts tagumori as a FUSE")
@click.argument("path", type=click.Path(path_type=Path, file_okay=False))
@click.pass_obj
def mount(lazy_vault: LazyVault, path: Path):
    from fuse import FUSE

    from tagumori.commands._mount_fs import TagumoriFS

    with lazy_vault as vault:
        FUSE(
            TagumoriFS(vault),
            str(path),
            foreground=True,
            nothreads=True,
            allow_other=True,
            entry_timeout="5",
            attr_timeout="5",
            negative_timeout="5",
        )
