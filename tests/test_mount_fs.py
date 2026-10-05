import stat
from pathlib import Path

import pytest
from fuse import FuseOSError

from tagumori.commands._mount_fs import TagumoriFS


@pytest.fixture
def fs(vault) -> TagumoriFS:
    return TagumoriFS(vault)


class TestRoot:
    def test_is_a_directory(self, fs):
        assert stat.S_ISDIR(fs.getattr("/", 0)["st_mode"])

    def test_lists_tags_and_queries(self, fs):
        assert fs.readdir("/", 0) == [".", "..", "tags", "queries"]

    def test_unknown_top_level_segment_raises_enoent(self, fs):
        with pytest.raises(FuseOSError):
            fs.getattr("/bogus", 0)

        with pytest.raises(FuseOSError):
            fs.readdir("/bogus", 0)

        with pytest.raises(FuseOSError):
            fs.readlink("/bogus/whatever")


class TestTagsRoute:
    def test_tags_root_is_a_directory(self, fs):
        assert stat.S_ISDIR(fs.getattr("/tags", 0)["st_mode"])

    def test_unknown_tag_raises_enoent(self, fs):
        with pytest.raises(FuseOSError):
            fs.getattr("/tags/bogus", 0)

    def test_known_tag_is_a_directory(self, fs, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])

        assert stat.S_ISDIR(fs.getattr("/tags/rock", 0)["st_mode"])

    def test_nested_tag_is_a_directory(self, fs, make_tagged_file):
        make_tagged_file("a.txt", [("genre", "rock")])

        assert stat.S_ISDIR(fs.getattr("/tags/genre/rock", 0)["st_mode"])

    def test_readdir_lists_child_tags_and_files(self, fs, make_tagged_file):
        make_tagged_file("a.txt", [("genre", "rock")])
        make_tagged_file("b.txt", [("genre",)])

        entries = fs.readdir("/tags/genre", 0)
        names = [e[0] if isinstance(e, tuple) else e for e in entries]

        assert "rock" in names
        assert "b.txt" in names

    def test_file_is_a_symlink_with_correct_target(self, fs, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])

        attrs = fs.getattr("/tags/rock/a.txt", 0)
        assert stat.S_ISLNK(attrs["st_mode"])
        assert fs.readlink("/tags/rock/a.txt") == str(Path("a.txt").resolve())

    def test_unknown_file_under_known_tag_raises_enoent(self, fs, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])

        with pytest.raises(FuseOSError):
            fs.getattr("/tags/rock/missing.txt", 0)


class TestQueriesRoute:
    def test_queries_root_is_a_directory(self, fs):
        assert stat.S_ISDIR(fs.getattr("/queries", 0)["st_mode"])

    def test_unknown_query_raises_enoent(self, fs):
        with pytest.raises(FuseOSError):
            fs.getattr("/queries/bogus", 0)

    def test_known_query_is_a_directory(self, fs, make_query):
        make_query("rock-files", select="rock")

        assert stat.S_ISDIR(fs.getattr("/queries/rock-files", 0)["st_mode"])

    def test_readdir_lists_matching_files(self, fs, make_query, make_tagged_file):
        make_tagged_file("a.txt", [("rock",)])
        make_query("rock-files", select="rock")

        entries = fs.readdir("/queries/rock-files", 0)
        names = [e[0] for e in entries if isinstance(e, tuple)]

        assert names == ["a.txt"]

    def test_file_is_a_symlink_with_correct_target(
        self, fs, make_query, make_tagged_file
    ):
        make_tagged_file("a.txt", [("rock",)])
        make_query("rock-files", select="rock")

        attrs = fs.getattr("/queries/rock-files/a.txt", 0)
        assert stat.S_ISLNK(attrs["st_mode"])
        assert fs.readlink("/queries/rock-files/a.txt") == str(Path("a.txt").resolve())

    def test_unknown_file_under_known_query_raises_enoent(self, fs, make_query):
        make_query("rock-files", select="rock")

        with pytest.raises(FuseOSError):
            fs.getattr("/queries/rock-files/missing.txt", 0)
