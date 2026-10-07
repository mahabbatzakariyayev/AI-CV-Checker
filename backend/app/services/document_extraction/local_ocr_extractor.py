from pathlib import Path

from app.schemas.extraction import ExtractedDocument, ExtractedPage
from app.services.document_extraction.base import DocumentExtractor


class LocalOCRExtractor(DocumentExtractor):
    def extract(self, file_path: Path) -> ExtractedDocument:
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            return ExtractedDocument(
                file_name=file_path.name,
                file_type=file_path.suffix.lower().lstrip("."),
                page_count=1,
                extraction_method="OCR_REQUIRED",
                full_text="",
                pages=[ExtractedPage(page_number=1, text="", confidence=0.0)],
                warnings=["OCR unavailable in local environment."],
                tables=[],
                detected_sections=[],
            )

        text = pytesseract.image_to_string(Image.open(file_path))
        return ExtractedDocument(
            file_name=file_path.name,
            file_type=file_path.suffix.lower().lstrip("."),
            page_count=1,
            extraction_method="ocr_tesseract",
            full_text=text,
            pages=[ExtractedPage(page_number=1, text=text, confidence=0.75)],
            warnings=[],
            tables=[],
            detected_sections=[],
        )
