from pathlib import Path

from app.services.document_extraction.local_text_extractor import LocalTextExtractor


def test_text_extraction(tmp_path: Path):
    file_path = tmp_path / "cv.txt"
    file_path.write_text("John Doe\nPython\nExperience", encoding="utf-8")
    doc = LocalTextExtractor().extract(file_path)
    assert "Python" in doc.full_text
    assert doc.page_count == 1
