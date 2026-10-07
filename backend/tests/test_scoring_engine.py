from app.config import get_settings
from app.schemas.candidate import CandidateProfile, CandidateSkills, WorkExperienceItem
from app.schemas.extraction import ExtractionQuality
from app.schemas.job_requirement import JobRequirementProfile, SkillRequirement
from app.services.llm.mock_llm_client import MockLLMClient
from app.services.scoring.scoring_engine import ScoringEngine


def _candidate() -> CandidateProfile:
    return CandidateProfile(
        candidate_id="c1",
        file_id="f1",
        candidate_name="A",
        email="a@example.com",
        phone="+123456789",
        total_years_experience=6,
        skills=CandidateSkills(
            programming_languages=["Python"],
            frameworks=["FastAPI"],
            cloud=["Azure OpenAI"],
            ai_ml=["RAG"],
            devops=["Docker"],
            databases=["Postgres"],
        ),
        work_experience=[
            WorkExperienceItem(
                company="X",
                role="Engineer",
                responsibilities=["Built backend APIs", "Led architecture decisions"],
                technologies=["Python", "FastAPI", "Azure OpenAI", "RAG"],
                achievements=["Production launch"],
            )
        ],
        extraction_quality=ExtractionQuality(
            quality_level="high",
            score=90,
            text_length=3000,
            page_count=2,
            has_email=True,
            has_phone=True,
            detected_sections=["experience", "education", "skills"],
            warnings=[],
            requires_manual_review=False,
        ),
    )


def _job() -> JobRequirementProfile:
    return JobRequirementProfile(
        job_title="Senior AI Engineer",
        minimum_years_experience=5,
        critical_skills=[SkillRequirement(skill="Python", normalized_skill="python", importance="critical", weight=80)],
        must_have_skills=[SkillRequirement(skill="Azure OpenAI", normalized_skill="azure openai", importance="must_have", weight=60)],
        required_languages=["English"],
        tools_and_platforms=["Azure"],
    )


def test_scoring_engine_returns_score():
    result = ScoringEngine().score_candidate(_candidate(), _job())
    assert result.total_score > 0
    assert result.total_score <= 1000
    assert result.max_possible_score_after_caps <= 1000


def test_scoring_engine_can_use_llm_hybrid_breakdown():
    settings = get_settings()
    previous = settings.scoring_mode
    settings.scoring_mode = "llm_hybrid"
    try:
        result = ScoringEngine(MockLLMClient()).score_candidate(_candidate(), _job())
        assert result.score_breakdown.eligibility_and_must_have_fit == 210
    finally:
        settings.scoring_mode = previous


def test_scoring_engine_treats_explicit_language_as_requirement_evidence():
    candidate = _candidate()
    candidate.languages = ["English", "Azerbaijani"]
    job = JobRequirementProfile(
        job_title="AI Engineer",
        critical_skills=[SkillRequirement(skill="English fluency", importance="critical")],
    )
    result = ScoringEngine().score_candidate(candidate, job)
    language_requirement = next(item for item in result.hard_requirement_results if item.requirement == "English fluency")
    assert language_requirement.status in {"met", "partial"}


def test_scoring_engine_can_use_llm_first_result():
    settings = get_settings()
    previous = settings.scoring_mode
    settings.scoring_mode = "llm_first"
    try:
        result = ScoringEngine(MockLLMClient()).score_candidate(_candidate(), _job())
        assert result.max_possible_score_after_caps == 1000
        assert result.recommendation_label in {"Recommended for Interview", "Needs Recruiter Review"}
        assert any("AI-first evaluation used" in note for note in result.strictness_notes)
    finally:
        settings.scoring_mode = previous
