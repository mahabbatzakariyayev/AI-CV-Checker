from app.schemas.candidate import CandidateProfile, CandidateSkills
from app.schemas.extraction import ExtractionQuality
from app.schemas.job_requirement import JobRequirementProfile
from app.services.scoring.score_caps import ScoreCapsService


def _candidate(level: str) -> CandidateProfile:
    return CandidateProfile(
        candidate_id="x",
        file_id="f",
        candidate_name="x",
        skills=CandidateSkills(programming_languages=["Python"]),
        extraction_quality=ExtractionQuality(
            quality_level=level,  # type: ignore[arg-type]
            score=30 if level == "low" else 90,
            text_length=100 if level == "low" else 2000,
            page_count=2,
            has_email=True,
            has_phone=True,
            detected_sections=["skills"],
            warnings=[],
            requires_manual_review=level == "low",
        ),
    )


def test_low_extraction_applies_cap():
    score, cap, notes, _ = ScoreCapsService().apply_caps(
        base_score=900,
        candidate=_candidate("low"),
        job=JobRequirementProfile(),
        critical_missing=[],
        evidence_strength_ratio=0.9,
    )
    assert cap == 649
    assert score <= 649
    assert notes
