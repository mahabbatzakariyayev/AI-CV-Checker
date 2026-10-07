import re

from app.schemas.extraction import ExtractedDocument, ExtractionQuality


class ExtractionQualityService:
    SECTION_PATTERNS = {
        "experience": re.compile(r"\b(experience|employment|work history)\b", re.IGNORECASE),
        "education": re.compile(r"\b(education|academic|degree)\b", re.IGNORECASE),
        "skills": re.compile(r"\b(skills|technologies|tech stack)\b", re.IGNORECASE),
    }
    EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    PHONE_PATTERN = re.compile(r"(\+\d{1,3}[\s\-]?)?(\(?\d{2,4}\)?[\s\-]?)?[\d\s\-]{6,}")

    def evaluate(self, doc: ExtractedDocument) -> ExtractionQuality:
        text = doc.full_text or ""
        text_length = len(text.strip())
        page_count = max(doc.page_count, 1)
        warnings = list(doc.warnings)
        score = 100

        has_email = bool(self.EMAIL_PATTERN.search(text))
        has_phone = bool(self.PHONE_PATTERN.search(text))
        if not has_email:
            score -= 12
            warnings.append("Email not detected.")
        if not has_phone:
            score -= 10
            warnings.append("Phone not detected.")

        detected_sections: list[str] = []
        for section, pattern in self.SECTION_PATTERNS.items():
            if pattern.search(text):
                detected_sections.append(section)
            else:
                score -= 7
        if text_length < 500 and page_count >= 2:
            score -= 30
            warnings.append("Text suspiciously short for multi-page document.")
        if text_length < 200:
            score -= 25
            warnings.append("Very low extracted text volume.")
        if any(not p.text.strip() for p in doc.pages):
            score -= 10
            warnings.append("One or more pages appear empty after extraction.")
        if doc.extraction_method == "OCR_REQUIRED":
            score = min(score, 20)
            warnings.append("OCR unavailable; extraction incomplete.")
        if "failed" in doc.extraction_method.lower():
            score = 0

        score = max(0, min(100, score))
        if score == 0:
            level = "failed"
        elif score >= 80:
            level = "high"
        elif score >= 60:
            level = "medium"
        else:
            level = "low"

        return ExtractionQuality(
            quality_level=level,
            score=score,
            text_length=text_length,
            page_count=page_count,
            has_email=has_email,
            has_phone=has_phone,
            detected_sections=detected_sections,
            warnings=list(dict.fromkeys(warnings)),
            requires_manual_review=level in {"low", "failed"},
        )
