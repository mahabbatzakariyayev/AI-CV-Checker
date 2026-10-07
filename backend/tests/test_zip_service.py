import zipfile
from pathlib import Path

import pytest

from app.services.zip_service import ZipService, ZipServiceError


def test_extract_zip_safely(tmp_path: Path):
    zip_path = tmp_path / "cvs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("a.txt", "candidate")
        zf.writestr("__MACOSX/._x", "ignore")

    output = tmp_path / "out"
    files = ZipService().extract_cv_zip(zip_path, output)
    assert len(files) == 1
    assert files[0].name == "a.txt"


def test_zip_slip_blocked(tmp_path: Path):
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.txt", "bad")

    with pytest.raises(ZipServiceError):
        ZipService().extract_cv_zip(zip_path, tmp_path / "out")
