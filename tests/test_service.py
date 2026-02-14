from tagumori import service


class TestSearchFiles:
    def test_select_nonexistent_tag_returns_empty(self, conn, tmp_path):
        """Selecting a tag that no file has should return no files, not all files."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["rock"], apply_tagalongs=False)

        result = service.execute_query(
            conn, select_strs=["nonexistent"], exclude_strs=[]
        )

        assert result == []

    def test_select_existing_tag_returns_matching_files(self, conn, tmp_path):
        """Selecting a tag should return only files with that tag."""
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], ["rock"], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], ["jazz"], apply_tagalongs=False)

        result = service.execute_query(conn, select_strs=["rock"], exclude_strs=[])

        assert len(result) == 1
        assert result[0] == file1.resolve()

    def test_exclude_only_returns_all_except_excluded(self, conn, tmp_path):
        """Excluding without selecting should return all files except excluded."""
        file1 = tmp_path / "rock.txt"
        file2 = tmp_path / "jazz.txt"
        file1.write_text("")
        file2.write_text("")

        service.add_tags_to_files(conn, [file1], ["rock"], apply_tagalongs=False)
        service.add_tags_to_files(conn, [file2], ["jazz"], apply_tagalongs=False)

        result = service.execute_query(conn, select_strs=[], exclude_strs=["rock"])

        assert len(result) == 1
        assert result[0] == file2.resolve()

    def test_select_case_sensitive_by_default(self, conn, tmp_path):
        """Tag search is case-sensitive by default."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["Rock"], apply_tagalongs=False)

        result = service.execute_query(conn, select_strs=["rock"], exclude_strs=[])

        assert result == []

    def test_select_ignore_tag_case(self, conn, tmp_path):
        """With ignore_tag_case, tag search should be case-insensitive."""
        file = tmp_path / "file.txt"
        file.write_text("")

        service.add_tags_to_files(conn, [file], ["Rock"], apply_tagalongs=False)

        result = service.execute_query(
            conn, select_strs=["rock"], exclude_strs=[], ignore_tag_case=True
        )

        assert len(result) == 1
        assert result[0] == file.resolve()
