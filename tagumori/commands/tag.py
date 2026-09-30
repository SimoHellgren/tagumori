import click

from tagumori.commands.common import regex_options
from tagumori.commands.context import LazyVault
from tagumori.utils import compile_matcher


@click.group(help="Tag management")
@click.pass_obj
def tag(lazy_vault: LazyVault):
    pass


@tag.command(help="Create new tag", name="create")
@click.option("-n", "--name", type=click.STRING, required=True)
@click.option("-c", "--category", type=click.STRING)
@click.pass_obj
def new_tag(lazy_vault: LazyVault, name: str, category: str | None):
    with lazy_vault as vault:
        vault.tags.create(name, category)


@tag.command(help="Edit tag", name="edit")
@click.argument("tag", nargs=-1, type=click.STRING, required=True)
@click.option("-n", "--name", type=click.STRING)
@click.option("-c", "--category", type=click.STRING)
@click.option(
    "--clear-category", type=click.BOOL, is_flag=True, help="Sets category to null."
)
@click.pass_obj
def edit_tag(lazy_vault: LazyVault, tag: list[str], clear_category: bool, **kwargs):
    if len(tag) > 1 and kwargs["name"]:
        raise click.BadArgumentUsage(
            "--name can't be present when multiple tags are given."
        )

    if not (any(kwargs.values()) or clear_category):
        raise click.BadArgumentUsage("Provide at least one option.")

    if clear_category and kwargs["category"]:
        raise click.BadArgumentUsage("Can't both set and clear category.")

    data = {k: v for k, v in kwargs.items() if v is not None}

    if clear_category:
        data["category"] = None

    with lazy_vault as vault:
        vault.tags.update(tag, data)


@tag.command(help="Replace all instances of a tag.", name="replace")
@click.argument("old", nargs=-1, type=click.STRING, required=True)
@click.option("-n", "--new", type=click.STRING, required=True)
@click.option(
    "--remove",
    type=click.BOOL,
    is_flag=True,
    help="Remove the replaced tags entirely.",
)
@click.pass_obj
def replace_tag(lazy_vault: LazyVault, old: tuple[str, ...], new: str, remove: bool):
    with lazy_vault as vault:
        new_record = vault.tags.get_or_create(new)
        olds = vault.tags.get_many_by_name(old)
        for old_record in olds:
            vault.file_tags.replace(old_record.id, new_record.id)

            if remove:
                vault.tags.delete(old_record.id)


@tag.command(help="Removes all instances of a tag.", name="delete")
@click.argument("tags", nargs=-1, type=click.STRING, required=True)
@click.pass_obj
def remove_tag(lazy_vault: LazyVault, tags: tuple[str, ...]):
    click.confirm(
        "Are you sure? This will also delete all child filetags of deleted tags.",
        abort=True,
    )

    with lazy_vault as vault:
        for tag in tags:
            if not (db_tag := vault.tags.get_by_name(tag)):
                raise click.ClickException(f"Tag '{tag}' not found in vault.")

            vault.tags.delete(db_tag.id)


@tag.command(help="List tags", name="ls")
@click.option("-l", "long", type=click.BOOL, is_flag=True, help="Long listing format.")
@regex_options
@click.pass_obj
def list_tags(
    lazy_vault: LazyVault,
    long: bool,
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
):
    with lazy_vault as vault:
        tags = sorted(vault.tags.get_all(), key=lambda x: x.name)

    matcher = compile_matcher(pattern, ignore_case, invert_match)

    for tag in filter(lambda t: matcher(t.name), tags):
        click.echo(tag.name + (f" ({tag.category})" if long else ""))
