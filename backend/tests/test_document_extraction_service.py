from pathlib import Path

from app.schemas.extraction import ExtractedDocument, ExtractedPage
from app.config import get_settings
from app.services.document_extraction.service import DocumentExtractionService


def test_image_extraction_requires_ocr_when_disabled(tmp_path: Path):
    settings = get_settings()
    previous = settings.enable_ocr
    settings.enable_ocr = False
    try:
        image_path = tmp_path / "cv.png"
        image_path.write_bytes(b"not-an-image")
        doc = DocumentExtractionService().extract(image_path)
        assert doc.extraction_method == "OCR_REQUIRED"
        assert "OCR is disabled" in " ".join(doc.warnings)
    finally:
        settings.enable_ocr = previous


def test_uses_azure_provider_when_enabled(tmp_path: Path):
    settings = get_settings()
    prev_provider = settings.document_intelligence_provider
    settings.document_intelligence_provider = "azure_document_intelligence"
    try:
        pdf_path = tmp_path / "cv.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")
        service = DocumentExtractionService()
        service.azure_extractor.extract = lambda _: ExtractedDocument(
            file_name="cv.pdf",
            file_type="pdf",
            page_count=1,
            extraction_method="azure_document_intelligence",
            full_text="hello",
            pages=[ExtractedPage(page_number=1, text="hello")],
            tables=[],
            detected_sections=[],
            warnings=[],
        )
        doc = service.extract(pdf_path)
        assert doc.extraction_method == "azure_document_intelligence"
    finally:
        settings.document_intelligence_provider = prev_provider
