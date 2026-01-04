PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS file (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tag (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT --might want to normalize later
);

CREATE TABLE IF NOT EXISTS file_tag (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES file(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tag(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES file_tag(id) ON DELETE CASCADE
);


/*
Indices to ensure uniqueness; UNIQUE(file_id, tag_id, parent_id)
do not work because parent_id is nullable and NULL != NULL.
These are called partial indices.
**/
CREATE UNIQUE INDEX IF NOT EXISTS file_tag_unique_root
ON file_tag (file_id, tag_id)
WHERE parent_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS file_tag_unique_child
ON file_tag (file_id, tag_id, parent_id)
WHERE parent_id IS NOT NULL;


CREATE TABLE IF NOT EXISTS tagalong (
    tag_id INTEGER REFERENCES tag(id) ON DELETE CASCADE,
    tagalong_id INTEGER REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (tag_id, tagalong_id)
);
