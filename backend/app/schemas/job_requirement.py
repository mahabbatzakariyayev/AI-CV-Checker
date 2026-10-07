from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SkillRequirement(BaseModel):
    skill: str
    normalized_skill: str | None = None
    importance: Literal["critical", "must_have", "nice_to_have"] = "must_have"
    weight: int = 0
    evidence_expectation: str = "explicit_work_evidence"
    synonyms: list[str] = Field(default_factory=list)

    @field_validator("normalized_skill", mode="before")
    @classmethod
    def coerce_normalized_skill(cls, value, info):
        if isinstance(value, str) and value.strip():
            return value.strip().lower().replace("-", "_").replace(" ", "_")
        data = getattr(info, "data", {}) or {}
        skill = data.get("skill")
        if not skill:
            return "unknown_skill"
        return str(skill).strip().lower().replace("-", "_").replace(" ", "_")

    @field_validator("importance", mode="before")
    @classmethod
    def coerce_importance(cls, value):
        if value is None:
            return "must_have"
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"critical", "must_have", "nice_to_have"}:
            return normalized
        if normalized in {"must", "required", "mandatory"}:
            return "must_have"
        if normalized in {"nice", "optional", "preferred"}:
            return "nice_to_have"
        return "must_have"

    @field_validator("weight", mode="before")
    @classmethod
    def coerce_weight(cls, value):
        if value is None:
            return 0
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @field_validator("synonyms", mode="before")
    @classmethod
    def coerce_synonyms(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if not isinstance(value, list):
            return []
        output: list[str] = []
        for item in value:
            if isinstance(item, str):
                output.append(item)
            elif isinstance(item, dict):
                candidate = item.get("name") or item.get("value") or item.get("skill")
                if candidate:
                    output.append(str(candidate))
            elif item is not None:
                output.append(str(item))
        return output


class ScoringWeights(BaseModel):
    eligibility_and_must_have_fit: int = 300
    technical_depth: int = 250
    relevant_professional_experience: int = 180
    project_and_achievement_evidence: int = 100
    seniority_and_ownership: int = 70
    education_and_certifications: int = 40
    communication_and_language: int = 30
    evidence_confidence: int = 30


class JobRequirementProfile(BaseModel):
    job_title: str | None = None
    seniority_level: str | None = None
    must_have_skills: list[SkillRequirement] = Field(default_factory=list)
    nice_to_have_skills: list[SkillRequirement] = Field(default_factory=list)
    critical_skills: list[SkillRequirement] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    minimum_years_experience: float | None = None
    required_education: list[str] = Field(default_factory=list)
    preferred_education: list[str] = Field(default_factory=list)
    required_certifications: list[str] = Field(default_factory=list)
    preferred_certifications: list[str] = Field(default_factory=list)
    required_languages: list[str] = Field(default_factory=list)
    location_requirements: list[str] = Field(default_factory=list)
    domain_preferences: list[str] = Field(default_factory=list)
    tools_and_platforms: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)

    @field_validator("must_have_skills", "nice_to_have_skills", "critical_skills", mode="before")
    @classmethod
    def coerce_skill_requirements(cls, value):
        if value is None:
            return []
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return []
        normalized: list[dict] = []
        for item in value:
            if isinstance(item, SkillRequirement):
                normalized.append(item.model_dump())
                continue
            if isinstance(item, str):
                normalized.append({"skill": item})
                continue
            if not isinstance(item, dict):
                continue
            skill_name = item.get("skill") or item.get("name") or item.get("title")
            if not skill_name:
                continue
            normalized.append(
                {
                    "skill": str(skill_name),
                    "normalized_skill": item.get("normalized_skill"),
                    "importance": item.get("importance") or item.get("priority"),
                    "weight": item.get("weight") or item.get("score"),
                    "evidence_expectation": item.get("evidence_expectation")
                    or item.get("evidence")
                    or "explicit_work_evidence",
                    "synonyms": item.get("synonyms") or [],
                }
            )
        return normalized

    @field_validator(
        "required_education",
        "preferred_education",
        "required_certifications",
        "preferred_certifications",
        "required_languages",
        "location_requirements",
        "domain_preferences",
        "tools_and_platforms",
        "disqualifiers",
        mode="before",
    )
    @classmethod
    def coerce_string_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                candidate = (
                    item.get("name")
                    or item.get("skill")
                    or item.get("value")
                    or item.get("title")
                    or item.get("tool")
                )
                if candidate:
                    normalized.append(str(candidate))
            elif item is not None:
                normalized.append(str(item))
        return normalized
