from pathlib import Path

import click

from tagumori.commands.context import LazyVault


@click.command(
    help="Mounts tagumori as a FUSE", context_settings={"show_default": True}
)
@click.argument("path", type=click.Path(path_type=Path, file_okay=False))
@click.option("--entry_timeout", default=5, type=int)
@click.option("--attr_timeout", default=5, type=int)
@click.option("--negative_timeout", default=5, type=int)
@click.pass_obj
def mount(
    lazy_vault: LazyVault,
    path: Path,
    entry_timeout: str,
    attr_timeout: str,
    negative_timeout: str,
):
    from fuse import FUSE

    from tagumori.commands._mount_fs import TagumoriFS

    with lazy_vault as vault:
        FUSE(
            TagumoriFS(vault),
            str(path),
            foreground=True,
            nothreads=True,
            allow_other=True,
            entry_timeout=str(entry_timeout),
            attr_timeout=str(attr_timeout),
            negative_timeout=str(negative_timeout),
        )
