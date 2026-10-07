from pathlib import Path

import pytest

from app.services.file_validation_service import FileValidationError, FileValidationService


def test_validate_supported_cv_file(tmp_path: Path):
    file_path = tmp_path / "cv.pdf"
    file_path.write_text("x", encoding="utf-8")
    FileValidationService().validate_cv_file(file_path)


def test_validate_rejects_unsupported_file(tmp_path: Path):
    file_path = tmp_path / "cv.exe"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(FileValidationError):
        FileValidationService().validate_cv_file(file_path)
