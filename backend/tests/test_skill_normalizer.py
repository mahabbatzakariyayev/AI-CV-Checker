from app.config import get_settings
from app.services.llm.mock_llm_client import MockLLMClient
from app.services.matching.skill_normalizer import SkillNormalizer


def test_skill_normalization_synonyms():
    norm = SkillNormalizer()
    assert norm.normalize("Azure Cognitive Search") == "azure ai search"
    assert norm.normalize("React.js") == "react"
    assert norm.normalize("MSSQL") == "sql server"


def test_skill_normalization_ai_assisted_for_unknown_alias():
    settings = get_settings()
    previous = settings.skill_normalization_mode
    settings.skill_normalization_mode = "ai_assisted"
    try:
        norm = SkillNormalizer(MockLLMClient())
        assert norm.normalize_list(["ReactJS"]) == ["react"]
    finally:
        settings.skill_normalization_mode = previous
