from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    claim: str
    source_text: str
    page_number: int | None = None
    section: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class ExtractedPage(BaseModel):
    page_number: int
    text: str = ""
    blocks: list[str] = Field(default_factory=list)
    confidence: float | None = None


class ExtractedTable(BaseModel):
    page_number: int | None = None
    rows: list[list[str]] = Field(default_factory=list)


class ExtractionQuality(BaseModel):
    quality_level: Literal["high", "medium", "low", "failed"]
    score: int
    text_length: int
    page_count: int
    has_email: bool
    has_phone: bool
    detected_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_manual_review: bool = False


class ExtractedDocument(BaseModel):
    file_name: str
    file_type: str
    page_count: int
    extraction_method: str
    full_text: str
    pages: list[ExtractedPage] = Field(default_factory=list)
    tables: list[ExtractedTable] = Field(default_factory=list)
    detected_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extraction_quality: ExtractionQuality | None = None
