from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.candidate import HardRequirementResult


class ScoreBreakdown(BaseModel):
    eligibility_and_must_have_fit: int = 0
    technical_depth: int = 0
    relevant_professional_experience: int = 0
    project_and_achievement_evidence: int = 0
    seniority_and_ownership: int = 0
    education_and_certifications: int = 0
    communication_and_language: int = 0
    evidence_confidence: int = 0

    def total(self) -> int:
        return (
            self.eligibility_and_must_have_fit
            + self.technical_depth
            + self.relevant_professional_experience
            + self.project_and_achievement_evidence
            + self.seniority_and_ownership
            + self.education_and_certifications
            + self.communication_and_language
            + self.evidence_confidence
        )


class CandidateScoreResult(BaseModel):
    candidate_id: str
    total_score: int
    max_possible_score_after_caps: int = 1000
    recommendation_label: str
    confidence_level: Literal["High", "Medium", "Low"]
    score_breakdown: ScoreBreakdown
    hard_requirement_results: list[HardRequirementResult] = Field(default_factory=list)
    critical_missing_requirements: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    strictness_notes: list[str] = Field(default_factory=list)


class NormalizedSkillItem(BaseModel):
    raw_skill: str
    normalized_skill: str
    confidence: Literal["high", "medium", "low"] = "medium"
    aliases: list[str] = Field(default_factory=list)


class SkillNormalizationResult(BaseModel):
    items: list[NormalizedSkillItem] = Field(default_factory=list)


class LLMScoreAssessment(BaseModel):
    total_score: int | None = None
    recommendation_label: str | None = None
    confidence_level: Literal["High", "Medium", "Low"] | None = None
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    hard_requirement_results: list[HardRequirementResult] = Field(default_factory=list)
    critical_missing_requirements: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    strictness_notes: list[str] = Field(default_factory=list)

    @field_validator("hard_requirement_results", mode="before")
    @classmethod
    def coerce_hard_requirement_results(cls, value):
        if value is None:
            return []
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return []
        output: list[dict] = []
        for item in value:
            if isinstance(item, HardRequirementResult):
                output.append(item.model_dump())
                continue
            if not isinstance(item, dict):
                continue
            requirement = item.get("requirement") or item.get("skill") or item.get("name") or item.get("title")
            if not requirement:
                continue
            status = str(item.get("status") or item.get("fit") or item.get("result") or "partial").strip().lower()
            if status not in {"met", "partial", "missing"}:
                status = "met" if status in {"yes", "match", "strong"} else "missing" if status in {"no", "gap"} else "partial"
            evidence = item.get("evidence") or item.get("reason") or item.get("justification") or item.get("summary") or "AI evaluation"
            output.append({"requirement": str(requirement), "status": status, "evidence": str(evidence)})
        return output

    @field_validator("critical_missing_requirements", "strengths", "gaps", "concerns", "evidence_summary", "strictness_notes", mode="before")
    @classmethod
    def coerce_string_lists(cls, value):
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
                candidate = item.get("text") or item.get("value") or item.get("name") or item.get("title")
                if candidate:
                    output.append(str(candidate))
            elif item is not None:
                output.append(str(item))
        return output

    @field_validator("confidence_level", mode="before")
    @classmethod
    def coerce_confidence_level(cls, value):
        if value is None:
            return None
        normalized = str(value).strip().lower()
        if normalized == "high":
            return "High"
        if normalized == "medium":
            return "Medium"
        if normalized == "low":
            return "Low"
        return "Medium"
