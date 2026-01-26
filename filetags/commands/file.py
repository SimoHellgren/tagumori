from enum import Enum
from pathlib import Path
from typing import Sequence

import click

from filetags import crud, service
from filetags.commands.context import LazyVault


class FileStatus(Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    INODE_MISMATCH = "mismatch"
    INODE_MISSING = "inode_missing"


def get_file_status(path: Path, record: dict):
    if not path.exists():
        return FileStatus.NOT_FOUND

    if not record["inode"]:
        return FileStatus.INODE_MISSING

    stat = path.stat()

    if not (record["inode"] == stat.st_ino and record["device"] == stat.st_dev):
        return FileStatus.INODE_MISMATCH

    return FileStatus.OK


@click.group(help="File management")
@click.pass_obj
def file(vault: LazyVault):
    pass


def print_box(title: str, lines: list[str]):
    width = max(len(click.unstyle(line)) for line in [title, *lines]) + 2

    click.echo(f"┌{'─' * width}┐")
    click.echo(f"│ {title.ljust(width - 1)}│")
    click.echo(f"├{'─' * width}┤")
    for line in lines:
        padding = width - 1 - len(click.unstyle(line))
        click.echo(f"│ {line}{' ' * padding}│")
    click.echo(f"└{'─' * width}┘")


def check_path(p: Path) -> dict:
    if p.exists():
        return {"text": "Exists", "fg": "green"}

    return {"text": "Not found", "fg": "red"}


def check_inode(p: Path, record: dict) -> dict:
    status = get_file_status(p, record)
    return {
        FileStatus.OK: {"text": "OK", "fg": "green"},
        FileStatus.INODE_MISMATCH: {"text": "Mismatch", "fg": "red"},
        FileStatus.INODE_MISSING: {"text": "Inode missing", "fg": "yellow"},
        FileStatus.NOT_FOUND: {"text": "OK", "fg": "green"},  # handled by check_path
    }[status]


@file.command(help="Show file info.")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path))
@click.option("-i", "--inode", type=int, help="Lookup by inode.")
@click.pass_obj
def info(vault: LazyVault, files: Sequence[Path], inode: int):
    if files and inode:
        raise click.UsageError("Cannot use both --inode and file paths")

    if not (files or inode):
        raise click.UsageError("Provide file path or --inode")

    with vault as conn:
        if inode is not None:
            records = crud.file.get_by_inode(conn, inode)

            if not records:
                return

            lookup_paths = [Path(r["path"]) for r in records]

        else:
            lookup_paths = files

        files_with_tags = service.get_files_with_tags(conn, lookup_paths)

    for path, data in files_with_tags.items():
        record = data["file"]
        roots = data["roots"]

        print_box(
            str(path),
            [
                f"Tags: {','.join(str(root) for root in roots)}",
                "Path: " + click.style(**check_path(path)),
                "Inode/device: " + click.style(**check_inode(path, record)),
            ],
        )


@file.command(help="Add files to db (without tags).")
@click.argument(
    "files", nargs=-1, type=click.Path(path_type=Path, exists=True, dir_okay=False)
)
@click.pass_obj
def add(vault: LazyVault, files: Sequence[Path]):
    with vault as conn:
        crud.file.get_or_create_many(conn, files)


@file.command(help="Drop files from db.")
@click.argument(
    "files", nargs=-1, type=click.Path(path_type=Path, exists=True, dir_okay=False)
)
@click.pass_obj
def drop(vault: LazyVault, files: Sequence[Path]):
    with vault as conn:
        records = crud.file.get_many_by_path(conn, files)
        click.confirm(
            f"Going do delete {len(records)} file(s). You sure about this", abort=True
        )
        for file in records:
            crud.file.delete(conn, file["id"])


@file.command(help="Edit file record.")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--refresh", is_flag=True, help="Use path to update inode/device")
@click.option(
    "--relocate",
    type=click.Path(path_type=Path),
    is_flag=False,
    flag_value=Path("."),
    default=None,
    help="Searches for file by inode/device (default: current dir)",
)
@click.option("--path", type=click.Path(path_type=Path, dir_okay=False, exists=True))
@click.pass_obj
def edit(
    vault: LazyVault,
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

    with vault as conn:
        records = crud.file.get_many_by_path(conn, files)
        if path:
            stat = path.stat()  # stat the new file
            crud.file.update(conn, records[0]["id"], path, stat.st_ino, stat.st_dev)

        elif refresh:
            for record in records:
                p = Path(record["path"])
                stat = p.stat()
                crud.file.update(conn, record["id"], p, stat.st_ino, stat.st_dev)

        elif relocate:
            for record in records:
                service.relocate_file(conn, record, relocate)


@file.command(help="Check file health.")
@click.option("--fix", is_flag=True, help="Fix missing inodes by refreshing from path")
@click.pass_obj
def check(vault: LazyVault, fix: bool):
    issues = []

    with vault as conn:
        all_files = crud.file.get_all(conn)

        for record in all_files:
            p = Path(record["path"])
            status = get_file_status(p, record)

            if status == FileStatus.OK:
                continue

            # Auto-fix missing inodes (file exists, just needs stat)
            if status == FileStatus.INODE_MISSING and fix:
                stat = p.stat()
                crud.file.update(conn, record["id"], p, stat.st_ino, stat.st_dev)
                issues.append((p, status, True))
            else:
                issues.append((p, status, False))

    if not issues:
        click.echo("No issues found.")
        return

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
def mv(vault: LazyVault, sources: Sequence[Path], dst: Path, force: bool):
    import shutil

    if not sources:
        raise click.UsageError("No source files provided")

    # Multiple sources require dst to be a directory
    if len(sources) > 1 and not dst.is_dir():
        raise click.UsageError(
            "Destination must be a directory when moving multiple files"
        )

    with vault as conn:
        for src in sources:
            record = crud.file.get_by_path(conn, src)

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
            crud.file.update(conn, record["id"], actual_dst, stat.st_ino, stat.st_dev)

            click.echo(f"Moved {src} -> {actual_dst}")
