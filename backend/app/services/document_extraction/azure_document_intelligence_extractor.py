from pathlib import Path

from app.config import get_settings
from app.schemas.extraction import ExtractedDocument, ExtractedPage, ExtractedTable
from app.services.document_extraction.base import DocumentExtractor


class AzureDocumentIntelligenceExtractor(DocumentExtractor):
    def __init__(self) -> None:
        self.settings = get_settings()

    def extract(self, file_path: Path) -> ExtractedDocument:
        endpoint = self.settings.azure_document_intelligence_endpoint.strip()
        key = self.settings.azure_document_intelligence_key.strip()
        if not endpoint or not key:
            raise RuntimeError("Azure Document Intelligence endpoint/key are not configured.")

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError as exc:
            raise RuntimeError(
                "azure-ai-documentintelligence package is required when DOCUMENT_INTELLIGENCE_PROVIDER=azure_document_intelligence."
            ) from exc

        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
            api_version=self.settings.azure_document_intelligence_api_version,
        )

        with file_path.open("rb") as stream:
            poller = client.begin_analyze_document(self.settings.azure_document_intelligence_model_id, body=stream)
            result = poller.result()

        pages: list[ExtractedPage] = []
        full_text_parts: list[str] = []

        for page in getattr(result, "pages", []) or []:
            page_number = getattr(page, "page_number", len(pages) + 1)
            lines = []
            for line in (getattr(page, "lines", None) or []):
                content = getattr(line, "content", "") or ""
                if content:
                    lines.append(content)
            page_text = "\n".join(lines)
            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=page_text,
                    blocks=lines,
                    confidence=None,
                )
            )
            full_text_parts.append(page_text)

        tables: list[ExtractedTable] = []
        for table in getattr(result, "tables", []) or []:
            page_number = None
            regions = getattr(table, "bounding_regions", None) or []
            if regions:
                page_number = getattr(regions[0], "page_number", None)

            row_count = int(getattr(table, "row_count", 0) or 0)
            col_count = int(getattr(table, "column_count", 0) or 0)
            rows = [["" for _ in range(col_count)] for _ in range(row_count)] if row_count and col_count else []
            for cell in getattr(table, "cells", []) or []:
                row_idx = int(getattr(cell, "row_index", 0) or 0)
                col_idx = int(getattr(cell, "column_index", 0) or 0)
                content = getattr(cell, "content", "") or ""
                if rows and row_idx < len(rows) and col_idx < len(rows[row_idx]):
                    rows[row_idx][col_idx] = content
            tables.append(ExtractedTable(page_number=page_number, rows=rows))

        full_text = (getattr(result, "content", None) or "\n".join(full_text_parts) or "").strip()
        warnings: list[str] = []
        if not full_text:
            warnings.append("Azure Document Intelligence returned no text content.")

        return ExtractedDocument(
            file_name=file_path.name,
            file_type=file_path.suffix.lower().lstrip("."),
            page_count=max(1, len(pages)),
            extraction_method="azure_document_intelligence",
            full_text=full_text,
            pages=pages or [ExtractedPage(page_number=1, text=full_text, blocks=[])],
            tables=tables,
            detected_sections=[],
            warnings=warnings,
        )
