from app.schemas.extraction import EvidenceItem, ExtractedDocument


def collect_evidence_from_text(claim: str, document: ExtractedDocument, needle: str) -> EvidenceItem | None:
    for page in document.pages:
        if needle.lower() in page.text.lower():
            lines = [line.strip() for line in page.text.splitlines() if line.strip()]
            snippet = next((line for line in lines if needle.lower() in line.lower()), page.text[:300])
            return EvidenceItem(
                claim=claim,
                source_text=snippet[:500],
                page_number=page.page_number,
                section=None,
                confidence="high",
            )
    return None
