import pytest

from app.services import tools


def test_read_file_rejects_path_traversal_and_wildcards():
    with pytest.raises(ValueError):
        tools.read_file("../README.md")
    with pytest.raises(ValueError):
        tools.read_file("*.html")
    with pytest.raises(ValueError):
        tools.read_file("nested/sop-001.html")


def test_read_file_accepts_plain_data_filename():
    content = tools.read_file("index.json")
    assert "documents" in content
