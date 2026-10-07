from app.config import get_settings
from app.services.llm.base import LLMClient
from app.utils.text_cleaning import lower_no_punct


class SkillNormalizer:
    SKILL_SYNONYMS: dict[str, str] = {
        "azure cognitive search": "azure ai search",
        "azure search": "azure ai search",
        "rag": "retrieval augmented generation",
        "retrieval-augmented generation": "retrieval augmented generation",
        "genai": "generative ai",
        "llm": "large language model",
        "ms sql": "sql server",
        "mssql": "sql server",
        "postgresql": "postgres",
        "js": "javascript",
        "ts": "typescript",
        "react.js": "react",
        "node.js": "node",
        "ci/cd": "continuous integration continuous deployment",
        "azure openai service": "azure openai",
        "openai on azure": "azure openai",
    }

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client
        self.settings = get_settings()
        self._cache: dict[str, str] = {}

    def normalize(self, skill: str) -> str:
        key = lower_no_punct(skill)
        if key in self.SKILL_SYNONYMS:
            return self.SKILL_SYNONYMS[key]
        if key in self._cache:
            return self._cache[key]
        return key

    def normalize_list(self, skills: list[str]) -> list[str]:
        if self.settings.skill_normalization_mode == "ai_assisted" and self.llm_client:
            self._normalize_unknown_skills(skills)
        seen: set[str] = set()
        result: list[str] = []
        for skill in skills:
            norm = self.normalize(skill)
            if norm not in seen:
                seen.add(norm)
                result.append(norm)
        return result

    def _normalize_unknown_skills(self, skills: list[str]) -> None:
        unknown: list[str] = []
        for skill in skills:
            key = lower_no_punct(skill)
            if not key:
                continue
            if key in self.SKILL_SYNONYMS or key in self._cache:
                continue
            unknown.append(skill)
        if not unknown:
            return
        result = self.llm_client.normalize_skills(unknown, context="Normalize skills for CV/job matching.")
        for item in result.items:
            key = lower_no_punct(item.raw_skill)
            value = lower_no_punct(item.normalized_skill)
            if key and value:
                self._cache[key] = value
