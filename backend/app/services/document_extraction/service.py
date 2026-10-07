from pathlib import Path

from app.config import get_settings
from app.schemas.extraction import ExtractedDocument, ExtractedPage
from app.services.document_extraction.azure_document_intelligence_extractor import AzureDocumentIntelligenceExtractor
from app.services.document_extraction.base import DocumentExtractor
from app.services.document_extraction.local_docx_extractor import LocalDocxExtractor
from app.services.document_extraction.local_ocr_extractor import LocalOCRExtractor
from app.services.document_extraction.local_pdf_extractor import LocalPDFExtractor
from app.services.document_extraction.local_text_extractor import LocalTextExtractor


class DocumentExtractionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.pdf_extractor = LocalPDFExtractor()
        self.docx_extractor = LocalDocxExtractor()
        self.text_extractor = LocalTextExtractor()
        self.ocr_extractor = LocalOCRExtractor()
        self.azure_extractor = AzureDocumentIntelligenceExtractor()

    def _choose_local_extractor(self, file_path: Path) -> DocumentExtractor:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return self.pdf_extractor
        if ext == ".docx":
            return self.docx_extractor
        if ext in {".txt"}:
            return self.text_extractor
        if ext in {".png", ".jpg", ".jpeg", ".tiff"}:
            return self.ocr_extractor
        if ext == ".doc":
            return self.text_extractor
        return self.text_extractor

    def extract(self, file_path: Path) -> ExtractedDocument:
        ext = file_path.suffix.lower()
        if ext in {".png", ".jpg", ".jpeg", ".tiff"} and not self.settings.enable_ocr:
            return ExtractedDocument(
                file_name=file_path.name,
                file_type=ext.lstrip("."),
                page_count=1,
                extraction_method="OCR_REQUIRED",
                full_text="",
                pages=[ExtractedPage(page_number=1, text="", confidence=0.0)],
                tables=[],
                detected_sections=[],
                warnings=["OCR is disabled. Set ENABLE_OCR=true to extract text from images."],
            )
        if ext == ".txt":
            return self.text_extractor.extract(file_path)
        if file_path.suffix.lower() == ".doc":
            return ExtractedDocument(
                file_name=file_path.name,
                file_type="doc",
                page_count=1,
                extraction_method="legacy_doc_unsupported",
                full_text="",
                pages=[ExtractedPage(page_number=1, text="")],
                tables=[],
                detected_sections=[],
                warnings=[
                    "Legacy .doc extraction is not supported in local mode. Convert to DOCX/PDF for reliable parsing."
                ],
            )
        if self.settings.document_intelligence_provider == "azure_document_intelligence":
            return self.azure_extractor.extract(file_path)
        extractor = self._choose_local_extractor(file_path)
        return extractor.extract(file_path)
