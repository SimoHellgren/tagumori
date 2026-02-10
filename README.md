# tagumori

From Japanese タグ森 (*tagumori*) — *tagu* (タグ, "tag") + *mori* (森, "forest"). A forest of tags.

Arbitrarily nestable tags for files, backed by SQLite.

## Install

Best to install with `pipx`.

Alternatively, yoy can `uv pip install -e .`


## Quick start

```bash
# initialize a vault
tagumori db init

# tag some files
tagumori add -f song.mp3 -t rock -t "artist[Led Zeppelin]"

# list files
tagumori ls
tagumori ls -s rock              # select by tag
tagumori ls -s rock -e jazz      # select and exclude
tagumori ls -l                   # long format (shows tags)

# manage files
tagumori file info song.mp3
tagumori file mv song.mp3 -t music/
tagumori file drop song.mp3
```

## Query syntax

Tags can be nested with brackets and combined with operators:

```
rock,artist[Led Zeppelin]     # AND
rock|jazz                     # OR
rock^jazz                     # XOR
!rock                         # NOT
genre[rock|jazz]              # nested: genre with child rock or jazz
~                             # root-level leaf / leaf inside brackets
*                             # any single tag
xor(a,b,c)                   # exactly one of
```

Operator precedence (highest first): `!`, `,`, `|`, `^`.

See [tagumori/query/algebra.md](tagumori/query/algebra.md) for the full algebra reference (distribution, negation semantics, wildcard identities, etc.).

## Tagalongs

Tagalongs automatically apply tags when another tag is present:

```bash
tagumori tagalong add -t "Led Zeppelin" -ta rock
tagumori tagalong apply
```

## Development

Requires WSL on Windows (inode/device tracking doesn't work on native Windows).

```bash
uv sync --extra dev
pytest
```
