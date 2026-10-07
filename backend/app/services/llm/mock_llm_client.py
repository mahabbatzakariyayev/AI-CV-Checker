import re

from app.schemas.candidate import CandidateProfile, CandidateSkills, ProjectItem, WorkExperienceItem
from app.schemas.extraction import EvidenceItem, ExtractedDocument
from app.schemas.job_requirement import JobRequirementProfile, SkillRequirement
from app.schemas.scoring import CandidateScoreResult, LLMScoreAssessment, NormalizedSkillItem, ScoreBreakdown, SkillNormalizationResult
from app.services.llm.base import LLMClient
from app.utils.text_cleaning import lower_no_punct


class MockLLMClient(LLMClient):
    EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    PHONE_PATTERN = re.compile(r"(\+\d{1,3}[\s\-]?)?(\(?\d{2,4}\)?[\s\-]?)?[\d\s\-]{7,}")

    SKILLS = [
        "python",
        "fastapi",
        "django",
        "react",
        "typescript",
        "javascript",
        "azure openai",
        "azure ai search",
        "retrieval augmented generation",
        "docker",
        "kubernetes",
        "postgres",
        "sql server",
        "aws",
        "azure",
        "gcp",
        "langchain",
        "langgraph",
        "llm",
        "generative ai",
    ]

    def __init__(self) -> None:
        self._debug_traces: list[dict] = []

    def extract_candidate_profile(self, candidate_id: str, file_id: str, document: ExtractedDocument) -> CandidateProfile:
        text = document.full_text
        lower = text.lower()
        email = self.EMAIL_PATTERN.search(text)
        phone = self.PHONE_PATTERN.search(text)

        found_skills = [skill for skill in self.SKILLS if skill in lower]
        evidence = [
            EvidenceItem(
                claim=f"Evidence for {skill}",
                source_text=self._extract_line(text, skill),
                page_number=self._guess_page(document, skill),
                section="skills_or_experience",
                confidence="high",
            )
            for skill in found_skills[:20]
        ]
        experience_years = self._extract_years_experience(lower)
        name = self._extract_name(text, document.file_name)

        work = []
        if "experience" in lower or "employment" in lower:
            work.append(
                WorkExperienceItem(
                    company=None,
                    role=None,
                    responsibilities=["Parsed from CV text in mock mode."],
                    technologies=found_skills[:10],
                    achievements=[],
                    evidence=evidence[:4],
                )
            )
        projects = []
        if "project" in lower:
            projects.append(
                ProjectItem(
                    name="Detected Project",
                    description="Project section detected in CV.",
                    technologies=found_skills[:8],
                    business_impact=None,
                    evidence=evidence[4:8],
                )
            )
        result = CandidateProfile(
            candidate_id=candidate_id,
            file_id=file_id,
            candidate_name=name,
            email=email.group(0) if email else None,
            phone=phone.group(0).strip() if phone else None,
            location=None,
            summary=None,
            total_years_experience=experience_years,
            skills=CandidateSkills(
                programming_languages=[s for s in found_skills if s in {"python", "javascript", "typescript"}],
                frameworks=[s for s in found_skills if s in {"fastapi", "django", "react", "langchain", "langgraph"}],
                cloud=[s for s in found_skills if s in {"azure", "aws", "gcp", "azure openai", "azure ai search"}],
                databases=[s for s in found_skills if s in {"postgres", "sql server"}],
                ai_ml=[s for s in found_skills if s in {"retrieval augmented generation", "llm", "generative ai"}],
                devops=[s for s in found_skills if s in {"docker", "kubernetes"}],
            ),
            work_experience=work,
            education=[],
            certifications=[],
            projects=projects,
            languages=["English"] if "english" in lower else [],
            achievements=[],
            publications=[],
            raw_evidence=evidence,
            extraction_quality=document.extraction_quality,  # type: ignore[arg-type]
        )
        self._debug_traces.append(
            {
                "provider": "mock",
                "operation": "extract_candidate_profile",
                "request_preview": text[:4000],
                "response_preview": "rule_based_mock_response",
                "parsed_preview": result.model_dump(mode="json"),
                "error": None,
            }
        )
        return result

    def extract_job_requirement(self, text: str) -> JobRequirementProfile:
        lower = text.lower()
        title = "Job Requirement"
        for line in text.splitlines():
            if len(line.strip()) > 5:
                title = line.strip()[:120]
                break
        must_have = []
        critical = []
        for skill in self.SKILLS:
            if skill in lower:
                entry = SkillRequirement(
                    skill=skill,
                    normalized_skill=skill,
                    importance="must_have",
                    weight=30,
                    synonyms=[],
                )
                if any(word in lower for word in ["critical", "must", "mandatory", "required"]) and skill in lower:
                    entry.importance = "critical"
                    entry.weight = 45
                    critical.append(entry)
                else:
                    must_have.append(entry)
        minimum_years = self._extract_min_experience(lower)
        required_languages = ["English"] if "english" in lower else []
        result = JobRequirementProfile(
            job_title=title,
            seniority_level="senior" if "senior" in lower else None,
            must_have_skills=must_have,
            critical_skills=critical,
            responsibilities=[line.strip() for line in text.splitlines() if len(line.strip()) > 20][:12],
            minimum_years_experience=minimum_years,
            required_languages=required_languages,
            tools_and_platforms=[s for s in ["azure", "aws", "gcp", "docker", "kubernetes"] if s in lower],
        )
        self._debug_traces.append(
            {
                "provider": "mock",
                "operation": "extract_job_requirement",
                "request_preview": text[:4000],
                "response_preview": "rule_based_mock_response",
                "parsed_preview": result.model_dump(mode="json"),
                "error": None,
            }
        )
        return result

    def generate_candidate_explanation(
        self, candidate: CandidateProfile, job: JobRequirementProfile, score: CandidateScoreResult
    ) -> dict:
        result = {
            "strengths": score.strengths,
            "gaps": score.gaps,
            "concerns": score.concerns,
            "evidence_summary": score.evidence_summary,
            "strictness_notes": score.strictness_notes,
        }
        self._debug_traces.append(
            {
                "provider": "mock",
                "operation": "generate_candidate_explanation",
                "request_preview": f"candidate={candidate.candidate_id}",
                "response_preview": "rule_based_mock_response",
                "parsed_preview": result,
                "error": None,
            }
        )
        return result

    def generate_interview_questions(
        self, candidate: CandidateProfile, job: JobRequirementProfile, score: CandidateScoreResult
    ) -> list[str]:
        questions: list[str] = []
        for skill in (job.critical_skills + job.must_have_skills)[:4]:
            questions.append(f"Can you explain your hands-on experience with {skill.skill}?")
        if "kubernetes" not in " ".join(candidate.skills.all_skills()).lower():
            questions.append("Kubernetes is not clearly evidenced. Have you deployed production services on Kubernetes?")
        if any("rag" in s for s in candidate.skills.all_skills()):
            questions.append("Can you explain your RAG architecture and how you evaluated retrieval quality?")
        result = questions[:8]
        self._debug_traces.append(
            {
                "provider": "mock",
                "operation": "generate_interview_questions",
                "request_preview": f"candidate={candidate.candidate_id}",
                "response_preview": "rule_based_mock_response",
                "parsed_preview": result,
                "error": None,
            }
        )
        return result

    def normalize_skills(self, skills: list[str], context: str = "") -> SkillNormalizationResult:
        synonym_map = {
            "azure cognitive search": "azure ai search",
            "azure search": "azure ai search",
            "rag": "retrieval augmented generation",
            "retrieval augmented generation": "retrieval augmented generation",
            "genai": "generative ai",
            "llm": "large language model",
            "mssql": "sql server",
            "postgresql": "postgres",
            "react js": "react",
            "reactjs": "react",
            "ts": "typescript",
            "js": "javascript",
        }
        items = []
        for skill in skills:
            key = lower_no_punct(skill)
            items.append(
                NormalizedSkillItem(
                    raw_skill=skill,
                    normalized_skill=synonym_map.get(key, key),
                    confidence="medium",
                    aliases=[],
                )
            )
        result = SkillNormalizationResult(items=items)
        self._debug_traces.append(
            {
                "provider": "mock",
                "operation": "normalize_skills",
                "request_preview": f"context={context[:500]} skills={skills}",
                "response_preview": "rule_based_mock_response",
                "parsed_preview": result.model_dump(mode="json"),
                "error": None,
            }
        )
        return result

    def score_candidate_structured(
        self, candidate: CandidateProfile, job: JobRequirementProfile
    ) -> LLMScoreAssessment:
        skills_blob = " ".join(candidate.skills.all_skills()).lower()
        has_python = "python" in skills_blob
        has_cloud = any(skill in skills_blob for skill in ["azure", "azure openai", "aws", "gcp"])
        has_projects = bool(candidate.projects)
        breakdown = ScoreBreakdown(
            eligibility_and_must_have_fit=210 if has_python else 80,
            technical_depth=min(250, 90 + len(candidate.skills.all_skills()) * 10),
            relevant_professional_experience=120 if candidate.work_experience else 30,
            project_and_achievement_evidence=75 if has_projects else 25,
            seniority_and_ownership=40 if (candidate.total_years_experience or 0) >= 5 else 18,
            education_and_certifications=20 if candidate.education or candidate.certifications else 8,
            communication_and_language=22 if candidate.languages else 10,
            evidence_confidence=20 if candidate.raw_evidence else 8,
        )
        result = LLMScoreAssessment(
            total_score=breakdown.total(),
            recommendation_label="Recommended for Interview" if has_python and has_projects else "Needs Recruiter Review",
            confidence_level="Medium",
            score_breakdown=breakdown,
            hard_requirement_results=[
                {
                    "requirement": "Python",
                    "status": "met" if has_python else "missing",
                    "evidence": "Mock AI evaluation detected Python evidence." if has_python else "Mock AI evaluation found no Python evidence.",
                }
            ],
            critical_missing_requirements=[] if has_python else ["Python"],
            strengths=[
                "AI rubric scoring found direct alignment in the extracted stack."
                if has_python
                else "Some technical alignment exists but evidence is incomplete."
            ],
            gaps=[] if has_cloud else ["Cloud/platform evidence is weaker than required."],
            concerns=[] if candidate.work_experience else ["Work history evidence is limited."],
            evidence_summary=[item.source_text for item in candidate.raw_evidence[:8]],
            strictness_notes=["LLM rubric scoring draft generated in mock mode."],
        )
        self._debug_traces.append(
            {
                "provider": "mock",
                "operation": "score_candidate_structured",
                "request_preview": f"candidate={candidate.candidate_id} job={job.job_title}",
                "response_preview": "rule_based_mock_response",
                "parsed_preview": result.model_dump(mode="json"),
                "error": None,
            }
        )
        return result

    def drain_debug_traces(self) -> list[dict]:
        traces = list(self._debug_traces)
        self._debug_traces.clear()
        return traces

    @staticmethod
    def _extract_line(text: str, token: str) -> str:
        for line in text.splitlines():
            if token.lower() in line.lower():
                return line.strip()[:500]
        return token

    @staticmethod
    def _guess_page(doc: ExtractedDocument, token: str) -> int:
        for page in doc.pages:
            if token.lower() in page.text.lower():
                return page.page_number
        return 1

    @staticmethod
    def _extract_years_experience(lower_text: str) -> float | None:
        matches = re.findall(r"(\d+)\+?\s+years", lower_text)
        if matches:
            return float(max(int(value) for value in matches))
        return None

    @staticmethod
    def _extract_min_experience(lower_text: str) -> float | None:
        matches = re.findall(r"(\d+)\+?\s+years", lower_text)
        if matches:
            return float(min(int(value) for value in matches))
        return None

    @staticmethod
    def _extract_name(text: str, file_name: str) -> str:
        for line in text.splitlines()[:8]:
            cleaned = line.strip()
            if 2 <= len(cleaned.split()) <= 4 and "@" not in cleaned and not any(ch.isdigit() for ch in cleaned):
                return cleaned[:100]
        return file_name.rsplit(".", 1)[0]
