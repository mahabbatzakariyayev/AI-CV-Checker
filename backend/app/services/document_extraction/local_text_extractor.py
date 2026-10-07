from pathlib import Path

from app.schemas.extraction import ExtractedDocument, ExtractedPage
from app.services.document_extraction.base import DocumentExtractor


class LocalTextExtractor(DocumentExtractor):
    def extract(self, file_path: Path) -> ExtractedDocument:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return ExtractedDocument(
            file_name=file_path.name,
            file_type=file_path.suffix.lower().lstrip("."),
            page_count=1,
            extraction_method="plain_text",
            full_text=text,
            pages=[ExtractedPage(page_number=1, text=text)],
            tables=[],
            detected_sections=[],
            warnings=[],
        )
