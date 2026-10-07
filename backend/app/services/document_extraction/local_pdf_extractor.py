from pathlib import Path

from app.config import get_settings
from app.schemas.extraction import ExtractedDocument, ExtractedPage
from app.services.document_extraction.base import DocumentExtractor


class LocalPDFExtractor(DocumentExtractor):
    def __init__(self) -> None:
        self.settings = get_settings()

    def extract(self, file_path: Path) -> ExtractedDocument:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for PDF extraction") from exc

        document = fitz.open(file_path)
        pages: list[ExtractedPage] = []
        full_text_parts: list[str] = []
        extracted_text_chars = 0
        image_based_pages = 0

        for idx, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            if len(text.strip()) < 10:
                image_based_pages += 1
            extracted_text_chars += len(text)
            pages.append(ExtractedPage(page_number=idx, text=text, blocks=[]))
            full_text_parts.append(text)

        method = "pdf_text"
        warnings: list[str] = []
        if image_based_pages == len(pages):
            method = "pdf_scanned_or_image_based"
            warnings.append("PDF appears scanned/image-based; OCR recommended.")
            if self.settings.enable_ocr:
                ocr_pages, ocr_warnings = self._ocr_pdf(document)
                if ocr_pages:
                    pages = ocr_pages
                    full_text_parts = [page.text for page in ocr_pages]
                    method = "pdf_ocr_tesseract"
                    warnings.append("OCR fallback applied to scanned PDF.")
                warnings.extend(ocr_warnings)
        elif extracted_text_chars < 200 and len(pages) > 1:
            warnings.append("Low text extracted relative to page count.")

        return ExtractedDocument(
            file_name=file_path.name,
            file_type="pdf",
            page_count=len(pages),
            extraction_method=method,
            full_text="\n".join(full_text_parts),
            pages=pages,
            tables=[],
            detected_sections=[],
            warnings=warnings,
        )

    def _ocr_pdf(self, document) -> tuple[list[ExtractedPage], list[str]]:
        try:
            from PIL import Image
            from pytesseract import Output
            import pytesseract
        except ImportError:
            return [], ["OCR libraries not installed for scanned PDF processing."]

        pages: list[ExtractedPage] = []
        warnings: list[str] = []
        for idx, page in enumerate(document, start=1):
            pix = page.get_pixmap(dpi=220)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(image) or ""
            confidence = None
            try:
                data = pytesseract.image_to_data(image, output_type=Output.DICT)
                conf_values = [float(item) for item in data.get("conf", []) if str(item).strip() not in {"-1", ""}]
                if conf_values:
                    confidence = round(sum(conf_values) / len(conf_values) / 100, 3)
            except Exception:
                warnings.append(f"OCR confidence unavailable for page {idx}.")
            pages.append(ExtractedPage(page_number=idx, text=text, blocks=[], confidence=confidence))
        return pages, warnings
