from app.services.llm.mock_llm_client import MockLLMClient
from app.services.parsing.job_requirement_service import JobRequirementService


def test_job_requirement_parsing_returns_schema():
    text = """
    Senior AI Engineer
    Must have Python, FastAPI, Azure OpenAI and RAG.
    Required: 5+ years experience.
    English required.
    """
    result = JobRequirementService(MockLLMClient()).parse(text)
    assert result.job_title
    assert result.minimum_years_experience == 5
    assert len(result.must_have_skills) + len(result.critical_skills) >= 1
