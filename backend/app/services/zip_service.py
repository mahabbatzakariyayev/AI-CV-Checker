import shutil
import zipfile
from pathlib import Path

from app.config import get_settings


IGNORED_NAMES = {"__MACOSX", ".DS_Store", "Thumbs.db"}


class ZipServiceError(Exception):
    pass


class ZipService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def extract_cv_zip(self, zip_path: Path, output_dir: Path) -> list[Path]:
        if not zip_path.exists():
            raise ZipServiceError("ZIP file not found")
        if zip_path.stat().st_size > self.settings.max_zip_size_bytes:
            raise ZipServiceError(f"ZIP exceeds max size {self.settings.max_zip_size_mb}MB")

        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        extracted_files: list[Path] = []
        with zipfile.ZipFile(zip_path, "r") as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if not members:
                raise ZipServiceError("ZIP is empty")
            if len(members) > self.settings.max_files_per_zip:
                raise ZipServiceError("ZIP has too many files")

            for member in members:
                normalized = Path(member.filename)
                if any(part in IGNORED_NAMES for part in normalized.parts):
                    continue
                if ".." in normalized.parts:
                    raise ZipServiceError(f"Unsafe path in ZIP: {member.filename}")
                if member.file_size > self.settings.max_file_size_bytes:
                    raise ZipServiceError(f"File too large in ZIP: {member.filename}")

                destination = (output_dir / normalized).resolve()
                if not str(destination).startswith(str(output_dir.resolve())):
                    raise ZipServiceError(f"Zip Slip attempt: {member.filename}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_files.append(destination)

        if not extracted_files:
            raise ZipServiceError("No usable files found after extraction")
        return extracted_files
