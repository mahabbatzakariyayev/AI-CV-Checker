from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.extraction import EvidenceItem, ExtractionQuality


class CandidateSkills(BaseModel):
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    ai_ml: list[str] = Field(default_factory=list)
    devops: list[str] = Field(default_factory=list)
    data_engineering: list[str] = Field(default_factory=list)
    business_tools: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)

    @field_validator(
        "programming_languages",
        "frameworks",
        "cloud",
        "databases",
        "ai_ml",
        "devops",
        "data_engineering",
        "business_tools",
        "soft_skills",
        "other",
        mode="before",
    )
    @classmethod
    def _coerce_string_lists(cls, value):
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
                candidate = item.get("name") or item.get("skill") or item.get("value")
                if candidate:
                    output.append(str(candidate))
            elif item is not None:
                output.append(str(item))
        return output

    def all_skills(self) -> list[str]:
        return (
            self.programming_languages
            + self.frameworks
            + self.cloud
            + self.databases
            + self.ai_ml
            + self.devops
            + self.data_engineering
            + self.business_tools
            + self.soft_skills
            + self.other
        )


class WorkExperienceItem(BaseModel):
    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration_months: int | None = None
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @field_validator("responsibilities", "technologies", "achievements", mode="before")
    @classmethod
    def _coerce_string_list_fields(cls, value):
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
                candidate = item.get("text") or item.get("value") or item.get("name")
                if candidate:
                    output.append(str(candidate))
            elif item is not None:
                output.append(str(item))
        return output


class EducationItem(BaseModel):
    degree: str | None = None
    field: str | None = None
    institution: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    business_impact: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @field_validator("technologies", mode="before")
    @classmethod
    def _coerce_tech_list(cls, value):
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


class CandidateProfile(BaseModel):
    candidate_id: str
    file_id: str
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    summary: str | None = None
    total_years_experience: float | None = None
    skills: CandidateSkills = Field(default_factory=CandidateSkills)
    work_experience: list[WorkExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    raw_evidence: list[EvidenceItem] = Field(default_factory=list)
    extraction_quality: ExtractionQuality | None = None

    @field_validator("work_experience", "education", "projects", "raw_evidence", mode="before")
    @classmethod
    def coerce_object_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        if isinstance(value, str):
            return []
        if not isinstance(value, list):
            return []
        return value

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills(cls, value):
        if value is None:
            return CandidateSkills()
        if isinstance(value, CandidateSkills):
            return value
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            skill_map = {
                "programming_language": "programming_languages",
                "programming_languages": "programming_languages",
                "language": "programming_languages",
                "framework": "frameworks",
                "frameworks": "frameworks",
                "cloud": "cloud",
                "database": "databases",
                "databases": "databases",
                "ai": "ai_ml",
                "ml": "ai_ml",
                "ai_ml": "ai_ml",
                "devops": "devops",
                "data_engineering": "data_engineering",
                "business_tools": "business_tools",
                "soft_skills": "soft_skills",
                "soft": "soft_skills",
            }
            out: dict[str, list[str]] = {
                "programming_languages": [],
                "frameworks": [],
                "cloud": [],
                "databases": [],
                "ai_ml": [],
                "devops": [],
                "data_engineering": [],
                "business_tools": [],
                "soft_skills": [],
                "other": [],
            }
            for item in value:
                if isinstance(item, str):
                    out["other"].append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("skill") or item.get("value")
                if not name:
                    continue
                category_raw = str(item.get("category") or item.get("type") or "other").lower()
                field_name = skill_map.get(category_raw, "other")
                out[field_name].append(str(name))
            return out
        return CandidateSkills()

    @field_validator("certifications", "languages", "achievements", "publications", mode="before")
    @classmethod
    def coerce_named_lists(cls, value):
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
                candidate = (
                    item.get("name")
                    or item.get("language")
                    or item.get("title")
                    or item.get("value")
                    or item.get("certification")
                )
                if candidate:
                    output.append(str(candidate))
            elif item is not None:
                output.append(str(item))
        return output


class HardRequirementResult(BaseModel):
    requirement: str
    status: Literal["met", "partial", "missing"]
    evidence: str | None = None
