from filetags import service
from filetags.models.node import Node


def tag(name: str) -> Node:
    """Helper to create a root node with a single tag child.

    This is a quirk of how expressions are parsed. Will likely fix when
    working on the grammar.
    """
    return Node("root", [Node(name)])


class TestSearchFiles:
    def test_select_nonexistent_tag_returns_empty(self, conn, tmp_path):
        """Selecting a tag that no file has should return no files, not all files."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], [Node("rock")], apply_tagalongs=False)

        result = service.search_files(
            conn, select_tags=[tag("nonexistent")], exclude_tags=[]
        )

        assert result == []

    def test_select_existing_tag_returns_matching_files(self, conn, tmp_path):
        """Selecting a tag should return only files with that tag."""
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], [Node("rock")], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], [Node("jazz")], apply_tagalongs=False)

        result = service.search_files(conn, select_tags=[tag("rock")], exclude_tags=[])

        assert len(result) == 1
        assert result[0]["path"] == str(file1.resolve())

    def test_exclude_only_returns_all_except_excluded(self, conn, tmp_path):
        """Excluding without selecting should return all files except excluded."""
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], [Node("rock")], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], [Node("jazz")], apply_tagalongs=False)

        result = service.search_files(conn, select_tags=[], exclude_tags=[tag("rock")])

        assert len(result) == 1
        assert result[0]["path"] == str(file2.resolve())
