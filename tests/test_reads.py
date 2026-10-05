from pathlib import Path

from tagumori import reads


class TestTagNames:
    def test_empty_vault_has_no_tags(self, vault):
        assert reads.tag_names(vault) == set()

    def test_returns_every_distinct_tag_name(self, vault, make_tagged_file):
        make_tagged_file("a.txt", [("genre", "rock")])
        make_tagged_file("b.txt", [("mood",)])

        assert reads.tag_names(vault) == {"genre", "rock", "mood"}

    def test_stale_until_cache_is_checked(self, vault, make_tagged_file):
        """Documents the contract: reads.py trusts the caller to call
        vault.check_cache() - it won't notice writes on its own."""
        assert reads.tag_names(vault) == set()

        make_tagged_file("a.txt", [("rock",)])

        assert reads.tag_names(vault) == set()

    def test_reflects_writes_once_cache_is_checked(self, vault, make_tagged_file):
        assert reads.tag_names(vault) == set()

        make_tagged_file("a.txt", [("rock",)])
        vault.check_cache()

        assert reads.tag_names(vault) == {"rock"}


class TestResolvePath:
    def test_matches_a_tag_at_any_depth(self, vault, make_tagged_file):
        """Root position isn't enforced - see reads.py's module docstring."""
        make_tagged_file("a.txt", [("genre", "rock")])

        ids = reads.resolve_path(vault, "/rock")

        assert len(ids) == 1

    def test_full_chain_must_match_exactly(self, vault, make_tagged_file):
        """Regression: resolve_path once returned ids from every depth of the
        recursive CTE, not just the final one - "/genre/rock" would include
        "genre"'s own id alongside the correct "rock"-under-"genre" id."""
        make_tagged_file("a.txt", [("genre", "rock")])

        genre_only = reads.resolve_path(vault, "/genre")
        full_chain = reads.resolve_path(vault, "/genre/rock")

        assert len(full_chain) == 1
        assert full_chain != genre_only
        assert not full_chain & genre_only

    def test_empty_if_chain_breaks(self, vault, make_tagged_file):
        make_tagged_file("a.txt", [("genre", "rock")])

        assert reads.resolve_path(vault, "/genre/jazz") == frozenset()

    def test_only_matches_the_given_parent(self, vault, make_tagged_file):
        """A tag name shared by two branches shouldn't cross-match."""
        make_tagged_file("a.txt", [("genre", "rock")])
        make_tagged_file("b.txt", [("mood", "rock")])

        under_genre = reads.resolve_path(vault, "/genre/rock")
        under_mood = reads.resolve_path(vault, "/mood/rock")

        assert len(under_genre) == 1
        assert len(under_mood) == 1
        assert under_genre != under_mood


class TestChildTags:
    def test_empty_ids_returns_empty_list(self, vault):
        assert reads.child_tags(vault, frozenset()) == []

    def test_returns_distinct_child_tag_names(self, vault, make_tagged_file):
        make_tagged_file("a.txt", [("genre", "rock")])
        make_tagged_file("b.txt", [("genre", "jazz")])

        ids = reads.resolve_path(vault, "/genre")

        assert set(reads.child_tags(vault, ids)) == {"rock", "jazz"}


class TestFilesByName:
    def test_empty_ids_returns_empty_dict(self, vault):
        """Regression: this used to return [] instead of {}, which crashed
        files_at/file_at (list has no .values()/.get())."""
        assert reads._files_by_name(vault, frozenset()) == {}

    def test_maps_basename_to_full_path(self, vault, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])

        ids = reads.resolve_path(vault, "/rock")
        result = reads._files_by_name(vault, ids)

        assert set(result) == {"a.txt"}
        assert Path(result["a.txt"]) == Path("a.txt").resolve()


class TestFilesAndFileAt:
    def test_files_at_empty_ids_returns_empty_list(self, vault):
        assert reads.files_at(vault, frozenset()) == []

    def test_files_at_returns_paths(self, vault, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])
        ids = reads.resolve_path(vault, "/rock")

        assert reads.files_at(vault, ids) == [str(Path("a.txt").resolve())]

    def test_file_at_returns_path_for_matching_name(self, vault, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])
        ids = reads.resolve_path(vault, "/rock")

        assert reads.file_at(vault, ids, "a.txt") == str(Path("a.txt").resolve())

    def test_file_at_returns_none_for_unknown_name(self, vault, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])
        ids = reads.resolve_path(vault, "/rock")

        assert reads.file_at(vault, ids, "missing.txt") is None


class TestQueryNames:
    def test_empty_vault_has_no_queries(self, vault):
        assert reads.query_names(vault) == set()

    def test_returns_saved_query_names(self, vault, make_query):
        make_query("rock-files", select="rock")
        make_query("jazz-files", select="jazz")

        assert reads.query_names(vault) == {"rock-files", "jazz-files"}


class TestFilesForQuery:
    def test_nonexistent_query_returns_empty(self, vault):
        assert reads.files_for_query(vault, "nonexistent") == []

    def test_matches_tag_at_any_depth(self, vault, make_query, make_tagged_file):
        """Same "root position isn't enforced" semantics as resolve_path -
        the saved query matches "rock" wherever it occurs in the tree."""
        make_tagged_file("a.txt", [("genre", "rock")])
        make_query("rock-files", select="rock")

        assert reads.files_for_query(vault, "rock-files") == [
            str(Path("a.txt").resolve())
        ]

    def test_excludes_non_matching_files(self, vault, make_query, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])
        make_tagged_file("b.txt", [("jazz",)])
        make_query("rock-files", select="rock")

        assert reads.files_for_query(vault, "rock-files") == [
            str(Path("a.txt").resolve())
        ]


class TestFileForQuery:
    def test_returns_path_for_matching_filename(self, vault, make_query, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])
        make_query("rock-files", select="rock")

        assert reads.file_for_query(vault, "rock-files", "a.txt") == str(
            Path("a.txt").resolve()
        )

    def test_returns_none_for_unknown_filename(self, vault, make_query, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])
        make_query("rock-files", select="rock")

        assert reads.file_for_query(vault, "rock-files", "missing.txt") is None

    def test_returns_none_for_unknown_query(self, vault):
        assert reads.file_for_query(vault, "nonexistent", "a.txt") is None
