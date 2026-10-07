from app.schemas.extraction import ExtractedDocument, ExtractedPage
from app.services.document_extraction.extraction_quality_service import ExtractionQualityService


def test_extraction_quality_low_for_short_multipage():
    doc = ExtractedDocument(
        file_name="cv.pdf",
        file_type="pdf",
        page_count=2,
        extraction_method="pdf_text",
        full_text="short text",
        pages=[ExtractedPage(page_number=1, text=""), ExtractedPage(page_number=2, text="short text")],
        tables=[],
        detected_sections=[],
        warnings=[],
    )
    quality = ExtractionQualityService().evaluate(doc)
    assert quality.quality_level in {"low", "failed"}
    assert quality.requires_manual_review is True
