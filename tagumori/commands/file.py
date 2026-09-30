from collections.abc import Sequence
from pathlib import Path

import click

from tagumori import service
from tagumori.commands.context import LazyVault
from tagumori.models import FileStatus
from tagumori.render import print_file_info


@click.group(help="File management")
@click.pass_obj
def file(lazy_vault: LazyVault):
    pass


@file.command(help="Show file info.")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path))
@click.option("-i", "--inode", type=int, help="Lookup by inode.")
@click.pass_obj
def info(lazy_vault: LazyVault, files: Sequence[Path], inode: int):
    if files and inode:
        raise click.UsageError("Cannot use both --inode and file paths")

    if not (files or inode):
        raise click.UsageError("Provide file path or --inode")

    with lazy_vault as vault:
        if inode is not None:
            records = vault.files.get_by_inode(inode)

            if not records:
                return

        else:
            records = vault.files.get_many_by_path(files)

        files_with_tags = service.lookup_tags(vault, records)

    for file in files_with_tags:
        print_file_info(file)


@file.command(help="Add files to db (without tags).")
@click.argument(
    "files", nargs=-1, type=click.Path(path_type=Path, exists=True, dir_okay=False)
)
@click.pass_obj
def add(lazy_vault: LazyVault, files: Sequence[Path]):
    with lazy_vault as vault:
        vault.files.get_or_create_many(files)


@file.command(help="Drop files from db.")
@click.argument(
    "files", nargs=-1, type=click.Path(path_type=Path, dir_okay=False), required=True
)
@click.pass_obj
def drop(lazy_vault: LazyVault, files: Sequence[Path]):
    with lazy_vault as vault:
        records = vault.files.get_many_by_path(files)
        click.confirm(
            f"Going do drop {len(records)} file(s) from database (file itself will remain on disk). You sure about this?",
            abort=True,
        )
        for file in records:
            vault.files.delete(file.id)


@file.command(help="Edit file record.")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--refresh", is_flag=True, help="Use path to update inode/device")
@click.option(
    "--relocate",
    type=click.Path(path_type=Path),
    is_flag=False,
    flag_value=Path("."),
    help="Searches for file by inode/device (default: current dir)",
)
@click.option("--path", type=click.Path(path_type=Path, dir_okay=False, exists=True))
@click.pass_obj
def edit(
    lazy_vault: LazyVault,
    files: Sequence[Path],
    refresh: bool,
    relocate: Path | None,
    path: Path | None,
):
    if not files:
        raise click.UsageError("No files provided")

    if (refresh + bool(relocate) + bool(path)) > 1:
        raise click.UsageError(
            "Can only provide one of:\n  --refresh\n  --relocate\n  --path"
        )

    if len(files) > 1 and path:
        raise click.UsageError("Can't provide multiple files and --path")

    with lazy_vault as vault:
        records = vault.files.get_many_by_path(files)
        if path:
            stat = path.stat()  # stat the new file
            vault.files.update(records[0].id, path, stat.st_ino, stat.st_dev)

        elif refresh:
            for record in records:
                p = Path(record.path)
                stat = p.stat()
                vault.files.update(record.id, p, stat.st_ino, stat.st_dev)

        elif relocate:
            for record in records:
                service.relocate_file(vault, record, relocate)


@file.command(help="Check file health.")
@click.option("--fix", is_flag=True, help="Fix missing inodes by refreshing from path")
@click.pass_obj
def check(lazy_vault: LazyVault, fix: bool):
    issues: list[tuple[Path, FileStatus, bool]] = []

    with lazy_vault as vault:
        all_files = vault.files.get_all()

        for record in all_files:
            p = Path(record.path)

            status = record.status()

            if status == FileStatus.OK:
                continue

            # Auto-fix missing inodes (file exists, just needs stat)
            if status == FileStatus.INODE_MISSING and fix:
                stat = p.stat()
                vault.files.update(record.id, p, stat.st_ino, stat.st_dev)
                issues.append((p, status, True))
            else:
                issues.append((p, status, False))

    if not issues:
        click.echo("No issues found.")
        return

    # TODO: extract styling to render
    for path, status, fixed in issues:
        label = {
            FileStatus.NOT_FOUND: click.style("NOT FOUND", fg="red"),
            FileStatus.INODE_MISMATCH: click.style("MISMATCH", fg="red"),
            FileStatus.INODE_MISSING: click.style("INODE MISSING", fg="yellow"),
        }[status]

        suffix = click.style(" (fixed)", fg="green") if fixed else ""
        click.echo(f"{path}  [{label}]{suffix}")


@file.command(help="Move tracked file(s) to a new location.")
@click.argument("sources", nargs=-1, type=click.Path(path_type=Path, exists=True))
@click.option("-t", "--to", "dst", required=True, type=click.Path(path_type=Path))
@click.option("-f", "--force", is_flag=True, help="Overwrite without confirmation")
@click.pass_obj
def mv(lazy_vault: LazyVault, sources: Sequence[Path], dst: Path, force: bool):
    import shutil

    if not sources:
        raise click.UsageError("No source files provided")

    # Multiple sources require dst to be a directory
    if len(sources) > 1 and not dst.is_dir():
        raise click.UsageError(
            "Destination must be a directory when moving multiple files"
        )

    with lazy_vault as vault:
        for src in sources:
            record = vault.files.get_by_path(src)

            if not record:
                raise click.ClickException(f"{src} is not tracked in the vault")

            # Determine actual destination path
            if dst.is_dir():
                actual_dst = dst / src.name
            else:
                actual_dst = dst

            if actual_dst.exists() and not force:
                click.confirm(f"{actual_dst} already exists. Overwrite?", abort=True)

            shutil.move(src, actual_dst)
            stat = actual_dst.stat()
            vault.files.update(record.id, actual_dst, stat.st_ino, stat.st_dev)

            click.echo(f"Moved {src} -> {actual_dst}")
