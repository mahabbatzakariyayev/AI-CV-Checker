from pathlib import Path

from app.config import get_settings


SUPPORTED_CV_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".tiff"}
SUPPORTED_JOB_EXTENSIONS = {".pdf", ".docx", ".txt"}


class FileValidationError(Exception):
    pass


class FileValidationService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def validate_cv_file(self, path: Path) -> None:
        if path.suffix.lower() not in SUPPORTED_CV_EXTENSIONS:
            raise FileValidationError(f"Unsupported CV file type: {path.suffix}")
        self._validate_common(path)

    def validate_job_file(self, path: Path) -> None:
        if path.suffix.lower() not in SUPPORTED_JOB_EXTENSIONS:
            raise FileValidationError(f"Unsupported job requirement file type: {path.suffix}")
        self._validate_common(path)

    def _validate_common(self, path: Path) -> None:
        if not path.exists():
            raise FileValidationError("File does not exist")
        if path.stat().st_size <= 0:
            raise FileValidationError("File is empty")
        if path.stat().st_size > self.settings.max_file_size_bytes:
            raise FileValidationError(f"File exceeds max size {self.settings.max_file_size_mb}MB")
