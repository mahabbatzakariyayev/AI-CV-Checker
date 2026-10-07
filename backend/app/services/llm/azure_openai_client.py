import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.config import get_settings
from app.schemas.candidate import CandidateProfile
from app.schemas.extraction import ExtractedDocument
from app.schemas.job_requirement import JobRequirementProfile
from app.schemas.scoring import CandidateScoreResult, LLMScoreAssessment, SkillNormalizationResult
from app.services.llm.base import LLMClient
from app.services.llm.prompts import (
    CANDIDATE_EXTRACTION_SYSTEM_PROMPT,
    EXPLANATION_SYSTEM_PROMPT,
    JOB_EXTRACTION_SYSTEM_PROMPT,
    LLM_SCORING_SYSTEM_PROMPT,
    SKILL_NORMALIZATION_SYSTEM_PROMPT,
)

ModelType = TypeVar("ModelType", bound=BaseModel)


class AzureOpenAIClient(LLMClient):
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self._debug_traces: list[dict] = []
        try:
            from langchain_openai import AzureChatOpenAI, ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("langchain-openai is required for Azure LLM backend") from exc

        deployment = settings.azure_openai_deployment
        if hasattr(settings, "azure_openai_chat_deployment") and getattr(settings, "azure_openai_chat_deployment"):
            deployment = getattr(settings, "azure_openai_chat_deployment")
        endpoint = settings.azure_openai_endpoint.strip()

        if "/openai/v1" in endpoint.rstrip("/"):
            self.chat_model = ChatOpenAI(
                base_url=endpoint.rstrip("/") + "/",
                api_key=settings.azure_openai_api_key,
                model=deployment,
                temperature=0.1,
            )
        else:
            self.chat_model = AzureChatOpenAI(
                azure_endpoint=endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_deployment=deployment,
                temperature=0.1,
            )

    def extract_candidate_profile(self, candidate_id: str, file_id: str, document: ExtractedDocument) -> CandidateProfile:
        prompt = (
            f"{CANDIDATE_EXTRACTION_SYSTEM_PROMPT}\n"
            f"candidate_id={candidate_id}\nfile_id={file_id}\n"
            "Return JSON for CandidateProfile.\n"
            f"Document:\n{document.model_dump_json()[:120000]}"
        )
        model = self._invoke_structured(prompt, CandidateProfile, operation="extract_candidate_profile")
        return model.model_copy(update={"candidate_id": candidate_id, "file_id": file_id, "extraction_quality": document.extraction_quality})

    def extract_job_requirement(self, text: str) -> JobRequirementProfile:
        prompt = (
            f"{JOB_EXTRACTION_SYSTEM_PROMPT}\n"
            "Return JSON for JobRequirementProfile with strict skill importance and weights.\n"
            f"Job text:\n{text[:120000]}"
        )
        return self._invoke_structured(prompt, JobRequirementProfile, operation="extract_job_requirement")

    def generate_candidate_explanation(
        self, candidate: CandidateProfile, job: JobRequirementProfile, score: CandidateScoreResult
    ) -> dict:
        prompt = (
            f"{EXPLANATION_SYSTEM_PROMPT}\n"
            "Return JSON object with keys: strengths, gaps, concerns, evidence_summary, strictness_notes.\n"
            f"Candidate:\n{candidate.model_dump_json()}\nJob:\n{job.model_dump_json()}\nScore:\n{score.model_dump_json()}"
        )
        response = self.chat_model.invoke(prompt).content
        parsed = self._load_json(response, dict)
        self._append_trace("generate_candidate_explanation", prompt=prompt, raw=response, parsed=parsed)
        return parsed

    def generate_interview_questions(
        self, candidate: CandidateProfile, job: JobRequirementProfile, score: CandidateScoreResult
    ) -> list[str]:
        prompt = (
            "Generate up to 8 technical interview questions as JSON list of strings.\n"
            "Use strengths, gaps, and critical requirements.\n"
            f"Candidate:\n{candidate.model_dump_json()}\nJob:\n{job.model_dump_json()}\nScore:\n{score.model_dump_json()}"
        )
        response = self.chat_model.invoke(prompt).content
        data = self._load_json(response, list)
        self._append_trace("generate_interview_questions", prompt=prompt, raw=response, parsed=data)
        return [str(item) for item in data][:8]

    def normalize_skills(self, skills: list[str], context: str = "") -> SkillNormalizationResult:
        prompt = (
            f"{SKILL_NORMALIZATION_SYSTEM_PROMPT}\n"
            "Return JSON for SkillNormalizationResult.\n"
            f"Context:\n{context[:8000]}\n"
            f"Skills:\n{json.dumps(skills, ensure_ascii=False)}"
        )
        raw = self.chat_model.invoke(prompt).content
        try:
            payload = self._json_payload(raw)
            coerced = self._coerce_skill_normalization_payload(payload, source_skills=skills)
            parsed = SkillNormalizationResult.model_validate(coerced)
            self._append_trace("normalize_skills", prompt=prompt, raw=raw, parsed=parsed.model_dump())
            return parsed
        except Exception as exc:
            self._append_trace("normalize_skills", prompt=prompt, raw=raw, error=str(exc))
            raise

    def score_candidate_structured(
        self, candidate: CandidateProfile, job: JobRequirementProfile
    ) -> LLMScoreAssessment:
        prompt = (
            f"{LLM_SCORING_SYSTEM_PROMPT}\n"
            "Return JSON for LLMScoreAssessment.\n"
            f"Candidate:\n{candidate.model_dump_json()}\n"
            f"Job:\n{job.model_dump_json()}"
        )
        return self._invoke_structured(prompt, LLMScoreAssessment, operation="score_candidate_structured")

    def _invoke_structured(self, prompt: str, schema: type[ModelType], operation: str) -> ModelType:
        raw = self.chat_model.invoke(prompt).content
        try:
            parsed = self._load_json(raw, schema)
            self._append_trace(operation, prompt=prompt, raw=raw, parsed=parsed.model_dump() if isinstance(parsed, BaseModel) else parsed)
            return parsed
        except Exception as exc:
            self._append_trace(operation, prompt=prompt, raw=raw, error=str(exc))
            raise

    def _load_json(self, raw: Any, expected_type: type) -> Any:
        payload = self._json_payload(raw)
        payload = self._coerce_payload(payload, expected_type)
        if isinstance(expected_type, type) and issubclass(expected_type, BaseModel):
            return expected_type.model_validate(payload)
        if expected_type == dict and isinstance(payload, dict):
            return payload
        if expected_type == list and isinstance(payload, list):
            return payload
        raise ValueError("Unexpected JSON response type from LLM")

    def _coerce_payload(self, payload: Any, expected_type: type) -> Any:
        if expected_type is CandidateProfile and isinstance(payload, dict):
            return self._coerce_candidate_profile_payload(payload)
        if expected_type is JobRequirementProfile and isinstance(payload, dict):
            return self._coerce_job_requirement_payload(payload)
        if expected_type is SkillNormalizationResult:
            return self._coerce_skill_normalization_payload(payload)
        if expected_type is LLMScoreAssessment and isinstance(payload, dict):
            return self._coerce_llm_score_payload(payload)
        return payload

    def _coerce_candidate_profile_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        contact = payload.get("contact") or {}
        skills = payload.get("skills")
        technical_skills = payload.get("technical_skills") or payload.get("technologies") or payload.get("tools_and_technologies")
        spoken_languages_from_skills: list[str] = []
        if isinstance(skills, dict):
            skill_languages = self._collect_strings(
                skills.get("programming_languages") or skills.get("languages") or skills.get("programming")
            )
            if skill_languages and all(self._looks_like_spoken_language(item) for item in skill_languages):
                spoken_languages_from_skills = skill_languages
                skill_languages = []
            normalized_skills = {
                "programming_languages": skill_languages,
                "frameworks": self._collect_strings(skills.get("frameworks") or skills.get("backend_frameworks")),
                "cloud": self._collect_strings(skills.get("cloud") or skills.get("cloud_platforms")),
                "databases": self._collect_strings(skills.get("databases")),
                "ai_ml": self._collect_strings(
                    skills.get("ai_ml") or skills.get("ai") or skills.get("machine_learning") or skills.get("llm")
                ),
                "devops": self._collect_strings(skills.get("devops") or skills.get("tools")),
                "data_engineering": self._collect_strings(skills.get("data_engineering")),
                "business_tools": self._collect_strings(skills.get("business_tools") or skills.get("platforms")),
                "soft_skills": self._collect_strings(skills.get("soft_skills")),
                "other": self._collect_strings(skills.get("other")),
            }
        else:
            normalized_skills = skills

        if isinstance(technical_skills, dict):
            normalized_skills = normalized_skills or {}
            if not isinstance(normalized_skills, dict):
                normalized_skills = {}
            normalized_skills["programming_languages"] = self._merge_unique(
                normalized_skills.get("programming_languages"),
                self._collect_strings(
                    technical_skills.get("programming_languages")
                    or technical_skills.get("languages")
                    or technical_skills.get("programming")
                ),
            )
            normalized_skills["frameworks"] = self._merge_unique(
                normalized_skills.get("frameworks"),
                self._collect_strings(
                    technical_skills.get("frameworks")
                    or technical_skills.get("backend_frameworks")
                    or technical_skills.get("frontend_frameworks")
                ),
            )
            normalized_skills["cloud"] = self._merge_unique(
                normalized_skills.get("cloud"),
                self._collect_strings(technical_skills.get("cloud") or technical_skills.get("cloud_platforms")),
            )
            normalized_skills["databases"] = self._merge_unique(
                normalized_skills.get("databases"),
                self._collect_strings(technical_skills.get("databases")),
            )
            normalized_skills["ai_ml"] = self._merge_unique(
                normalized_skills.get("ai_ml"),
                self._collect_strings(
                    technical_skills.get("ai_ml")
                    or technical_skills.get("ai")
                    or technical_skills.get("machine_learning")
                    or technical_skills.get("llm")
                ),
            )
            normalized_skills["devops"] = self._merge_unique(
                normalized_skills.get("devops"),
                self._collect_strings(technical_skills.get("devops") or technical_skills.get("tools")),
            )
            normalized_skills["business_tools"] = self._merge_unique(
                normalized_skills.get("business_tools"),
                self._collect_strings(technical_skills.get("business_tools") or technical_skills.get("platforms")),
            )
            normalized_skills["other"] = self._merge_unique(
                normalized_skills.get("other"),
                self._collect_strings(technical_skills.get("other")),
            )
        elif isinstance(technical_skills, list):
            if isinstance(normalized_skills, dict):
                normalized_skills["other"] = self._merge_unique(normalized_skills.get("other"), self._collect_strings(technical_skills))
            elif not normalized_skills:
                normalized_skills = technical_skills

        experience_source = payload.get("work_experience") or payload.get("experience") or payload.get("professional_experience")
        work_items = []
        for item in self._ensure_list(experience_source):
            if not isinstance(item, dict):
                continue
            work_items.append(
                {
                    "company": item.get("company") or item.get("employer") or item.get("organization"),
                    "role": item.get("role") or item.get("job_title") or item.get("title"),
                    "start_date": item.get("start_date") or item.get("from"),
                    "end_date": item.get("end_date") or item.get("to"),
                    "duration_months": item.get("duration_months"),
                    "responsibilities": self._collect_strings(item.get("responsibilities") or item.get("description")),
                    "technologies": self._collect_strings(item.get("technologies") or item.get("skills")),
                    "achievements": self._collect_strings(item.get("achievements") or item.get("impact")),
                    "evidence": item.get("evidence") or [],
                }
            )

        education_items = []
        for item in self._ensure_list(payload.get("education") or payload.get("academic_background")):
            if not isinstance(item, dict):
                continue
            education_items.append(
                {
                    "degree": item.get("degree"),
                    "field": item.get("field") or item.get("major"),
                    "institution": item.get("institution") or item.get("school") or item.get("university"),
                    "start_year": item.get("start_year"),
                    "end_year": item.get("end_year") or item.get("graduation_year"),
                    "evidence": item.get("evidence") or [],
                }
            )

        project_items = []
        for item in self._ensure_list(payload.get("projects") or payload.get("project_experience")):
            if not isinstance(item, dict):
                continue
            project_items.append(
                {
                    "name": item.get("name") or item.get("title"),
                    "description": item.get("description") or item.get("summary"),
                    "technologies": self._collect_strings(item.get("technologies") or item.get("skills")),
                    "business_impact": item.get("business_impact") or item.get("impact"),
                    "evidence": item.get("evidence") or [],
                }
            )

        languages = payload.get("languages") or payload.get("language_skills") or spoken_languages_from_skills or []

        return {
            "candidate_id": payload.get("candidate_id"),
            "file_id": payload.get("file_id"),
            "candidate_name": payload.get("candidate_name") or payload.get("full_name") or payload.get("name"),
            "email": payload.get("email") or contact.get("email"),
            "phone": payload.get("phone") or contact.get("phone"),
            "location": payload.get("location") or contact.get("location"),
            "linkedin_url": payload.get("linkedin_url") or contact.get("linkedin"),
            "github_url": payload.get("github_url") or contact.get("github"),
            "portfolio_url": payload.get("portfolio_url") or contact.get("portfolio"),
            "summary": payload.get("summary") or payload.get("headline") or payload.get("profile"),
            "total_years_experience": payload.get("total_years_experience") or payload.get("years_experience"),
            "skills": normalized_skills,
            "work_experience": work_items,
            "education": education_items,
            "certifications": payload.get("certifications") or payload.get("licenses") or [],
            "projects": project_items,
            "languages": languages,
            "achievements": payload.get("achievements") or [],
            "publications": payload.get("publications") or [],
            "raw_evidence": payload.get("raw_evidence") or payload.get("evidence") or [],
            "extraction_quality": payload.get("extraction_quality"),
        }

    def _coerce_job_requirement_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        skills = payload.get("skills") or {}
        language_requirements = payload.get("language_requirements") or []
        experience_requirements = payload.get("experience_requirements") or []
        nice_tools = payload.get("tools_and_platforms") or []
        must_have_skills = payload.get("must_have_skills")
        critical_skills = payload.get("critical_skills")
        nice_to_have_skills = payload.get("nice_to_have_skills")

        if isinstance(skills, dict):
            critical_skills = critical_skills or skills.get("critical")
            must_have_skills = must_have_skills or skills.get("must_have")
            nice_to_have_skills = nice_to_have_skills or skills.get("nice_to_have")
        elif isinstance(skills, list):
            normalized_entries = []
            for item in skills:
                if isinstance(item, str):
                    normalized_entries.append({"skill": item, "importance": "must_have"})
                    continue
                if not isinstance(item, dict):
                    continue
                normalized_entries.append(
                    {
                        "skill": item.get("skill") or item.get("name") or item.get("title"),
                        "importance": item.get("importance")
                        or ("must_have" if item.get("required") else "nice_to_have"),
                        "weight": item.get("weight") or item.get("score"),
                        "synonyms": item.get("synonyms") or item.get("aliases") or [],
                        "evidence_expectation": item.get("evidence_expectation") or item.get("evidence"),
                    }
                )
            critical_skills = critical_skills or [item for item in normalized_entries if item.get("importance") == "critical"]
            must_have_skills = must_have_skills or [item for item in normalized_entries if item.get("importance") in {"must_have", "required", None}]
            nice_to_have_skills = nice_to_have_skills or [
                item for item in normalized_entries if item.get("importance") in {"nice_to_have", "preferred", "optional"}
            ]
        critical_skills = critical_skills or payload.get("critical_requirements")
        must_have_skills = must_have_skills or payload.get("must_have_requirements")
        nice_to_have_skills = nice_to_have_skills or payload.get("nice_to_have_requirements")

        required_languages = payload.get("required_languages")
        if not required_languages and language_requirements:
            required_languages = [item.get("language") if isinstance(item, dict) else item for item in language_requirements]

        if not nice_tools and experience_requirements:
            extracted_tools = []
            for item in experience_requirements:
                if isinstance(item, dict):
                    area = item.get("area")
                    if area:
                        extracted_tools.append(area)
            nice_tools = extracted_tools

        responsibilities = payload.get("responsibilities") or payload.get("key_responsibilities") or []
        if isinstance(responsibilities, str):
            responsibilities = [responsibilities]

        return {
            "job_title": payload.get("job_title") or payload.get("title"),
            "seniority_level": payload.get("seniority_level") or payload.get("seniority"),
            "must_have_skills": must_have_skills or [],
            "nice_to_have_skills": nice_to_have_skills or [],
            "critical_skills": critical_skills or [],
            "responsibilities": responsibilities,
            "minimum_years_experience": payload.get("minimum_years_experience") or payload.get("years_experience"),
            "required_education": payload.get("required_education") or [],
            "preferred_education": payload.get("preferred_education") or [],
            "required_certifications": payload.get("required_certifications") or [],
            "preferred_certifications": payload.get("preferred_certifications") or [],
            "required_languages": required_languages or [],
            "location_requirements": payload.get("location_requirements") or ([payload.get("location")] if payload.get("location") else []),
            "domain_preferences": payload.get("domain_preferences") or ([payload.get("industry")] if payload.get("industry") else []),
            "tools_and_platforms": nice_tools or [],
            "disqualifiers": payload.get("disqualifiers") or [],
            "scoring_weights": payload.get("scoring_weights") or {},
        }

    def _coerce_skill_normalization_payload(self, payload: Any, source_skills: list[str] | None = None) -> dict[str, Any]:
        if isinstance(payload, dict) and "items" in payload:
            return payload
        items = []
        source = []
        if isinstance(payload, dict) and isinstance(payload.get("skills"), list):
            source = payload["skills"]
        elif isinstance(payload, dict) and isinstance(payload.get("normalized_skills"), list):
            normalized = payload["normalized_skills"]
            originals = source_skills or normalized
            for index, item in enumerate(normalized):
                raw_skill = originals[index] if index < len(originals) else item
                if item is None:
                    continue
                items.append(
                    {
                        "raw_skill": raw_skill,
                        "normalized_skill": item,
                        "confidence": "medium",
                        "aliases": [],
                    }
                )
            return {"items": items}
        elif isinstance(payload, list):
            source = payload
        for item in source:
            if isinstance(item, str):
                items.append(
                    {
                        "raw_skill": item,
                        "normalized_skill": item,
                        "confidence": "medium",
                        "aliases": [],
                    }
                )
            elif isinstance(item, dict):
                raw_skill = item.get("raw_skill") or item.get("skill") or item.get("name") or item.get("value")
                normalized_skill = item.get("normalized_skill") or item.get("canonical_skill") or raw_skill
                if raw_skill:
                    items.append(
                        {
                            "raw_skill": raw_skill,
                            "normalized_skill": normalized_skill,
                            "confidence": item.get("confidence") or "medium",
                            "aliases": item.get("aliases") or [],
                        }
                    )
        return {"items": items}

    @staticmethod
    def _json_payload(raw: Any) -> Any:
        if isinstance(raw, (list, dict)):
            return raw
        text = str(raw).strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def _coerce_llm_score_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        hard_requirements = payload.get("hard_requirement_results") or payload.get("hard_requirements") or payload.get("requirement_results")
        if not hard_requirements and isinstance(payload.get("skill_assessment"), list):
            hard_requirements = []
            for item in payload["skill_assessment"]:
                if not isinstance(item, dict):
                    continue
                hard_requirements.append(
                    {
                        "requirement": item.get("skill") or item.get("name"),
                        "status": item.get("status")
                        or ("met" if (item.get("score") or 0) >= (item.get("max_score") or 1) * 0.85 else "partial" if (item.get("score") or 0) > 0 else "missing"),
                        "evidence": item.get("evidence") or item.get("reason") or item.get("justification") or "AI evaluation",
                    }
                )
        return {
            "total_score": payload.get("total_score") or payload.get("overall_score") or payload.get("final_score"),
            "recommendation_label": payload.get("recommendation_label") or payload.get("recommendation") or payload.get("label"),
            "confidence_level": payload.get("confidence_level") or payload.get("confidence"),
            "score_breakdown": payload.get("score_breakdown") or payload.get("category_scores") or {},
            "hard_requirement_results": hard_requirements or [],
            "critical_missing_requirements": payload.get("critical_missing_requirements") or payload.get("critical_gaps") or [],
            "strengths": self._collect_strings(payload.get("strengths")),
            "gaps": self._collect_strings(payload.get("gaps")),
            "concerns": self._collect_strings(payload.get("concerns")),
            "evidence_summary": self._collect_strings(payload.get("evidence_summary")),
            "strictness_notes": self._collect_strings(
                payload.get("strictness_notes") or payload.get("category_justifications")
            ),
        }

    @staticmethod
    def _ensure_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _collect_strings(value: Any) -> list[str]:
        items = AzureOpenAIClient._ensure_list(value)
        result: list[str] = []
        for item in items:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                candidate = (
                    item.get("name")
                    or item.get("value")
                    or item.get("skill")
                    or item.get("text")
                    or item.get("title")
                    or item.get("language")
                )
                if candidate:
                    result.append(str(candidate))
            elif item is not None:
                result.append(str(item))
        return result

    @staticmethod
    def _merge_unique(existing: Any, new_values: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for item in AzureOpenAIClient._collect_strings(existing) + new_values:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged

    @staticmethod
    def _looks_like_spoken_language(value: str) -> bool:
        normalized = value.strip().lower()
        return normalized in {
            "english",
            "french",
            "turkish",
            "azerbaijani",
            "azerbaijanian",
            "russian",
            "spanish",
            "german",
            "arabic",
            "native",
            "beginner",
        }

    def drain_debug_traces(self) -> list[dict]:
        traces = list(self._debug_traces)
        self._debug_traces.clear()
        return traces

    def _append_trace(
        self,
        operation: str,
        *,
        prompt: str,
        raw: Any | None = None,
        parsed: Any | None = None,
        error: str | None = None,
    ) -> None:
        max_chars = 6000
        self._debug_traces.append(
            {
                "provider": "azure_openai",
                "operation": operation,
                "model": self.settings.azure_openai_chat_deployment or self.settings.azure_openai_deployment,
                "request_preview": self._truncate(prompt, max_chars),
                "response_preview": self._truncate(raw, max_chars) if raw is not None else None,
                "parsed_preview": self._truncate(parsed, max_chars) if parsed is not None else None,
                "error": error,
            }
        )

    @staticmethod
    def _truncate(value: Any, max_chars: int) -> str:
        if isinstance(value, str):
            text = value
        else:
            try:
                text = json.dumps(value, ensure_ascii=False)
            except Exception:
                text = str(value)
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars]}... [truncated {len(text) - max_chars} chars]"
