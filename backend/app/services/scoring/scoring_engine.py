from app.config import get_settings
from app.schemas.candidate import CandidateProfile, HardRequirementResult
from app.schemas.job_requirement import JobRequirementProfile, SkillRequirement
from app.schemas.scoring import CandidateScoreResult, LLMScoreAssessment, ScoreBreakdown
from app.services.llm.base import LLMClient
from app.services.matching.semantic_matcher import SemanticMatcher
from app.services.matching.skill_normalizer import SkillNormalizer
from app.services.scoring.recommendation_service import RecommendationService
from app.services.scoring.score_caps import ScoreCapsService
from app.utils.text_cleaning import lower_no_punct


class ScoringEngine:
    REQUIREMENT_STOPWORDS = {
        "and",
        "or",
        "with",
        "other",
        "such",
        "using",
        "experience",
        "familiarity",
        "ability",
        "skills",
        "skill",
        "strong",
        "working",
        "written",
        "spoken",
        "platform",
        "platforms",
        "fluency",
        "knowledge",
    }

    CATEGORY_MAXIMA = {
        "eligibility_and_must_have_fit": 300,
        "technical_depth": 250,
        "relevant_professional_experience": 180,
        "project_and_achievement_evidence": 100,
        "seniority_and_ownership": 70,
        "education_and_certifications": 40,
        "communication_and_language": 30,
        "evidence_confidence": 30,
    }

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.settings = get_settings()
        self.llm_client = llm_client
        self.skill_normalizer = SkillNormalizer(llm_client)
        self.semantic_matcher = SemanticMatcher()
        self.caps_service = ScoreCapsService()
        self.recommendation_service = RecommendationService()

    def score_candidate(self, candidate: CandidateProfile, job: JobRequirementProfile) -> CandidateScoreResult:
        if self.settings.scoring_mode == "llm_first" and self.llm_client:
            return self._score_candidate_ai_first(candidate, job)

        normalized_candidate_skills = self.skill_normalizer.normalize_list(candidate.skills.all_skills())
        critical_missing: list[str] = []
        hard_requirements: list[HardRequirementResult] = []
        eligibility_points = 0

        must_have_points = 180
        critical_skills = job.critical_skills or []
        must_have_skills = job.must_have_skills or []
        self.skill_normalizer.normalize_list(
            [req.skill for req in critical_skills + must_have_skills]
            + [synonym for req in critical_skills + must_have_skills for synonym in req.synonyms]
        )
        all_required_skills = critical_skills + must_have_skills
        points_per_skill = must_have_points / max(1, len(all_required_skills))
        evidence_hits = 0
        evidence_total = 0

        for req in critical_skills:
            result, points, evidence = self._score_skill_requirement(req, candidate, normalized_candidate_skills, points_per_skill)
            hard_requirements.append(HardRequirementResult(requirement=req.skill, status=result, evidence=evidence))
            eligibility_points += int(points)
            evidence_total += 1
            if result == "missing":
                critical_missing.append(req.skill)
            if result in {"met", "partial"}:
                evidence_hits += 1

        for req in must_have_skills:
            result, points, evidence = self._score_skill_requirement(req, candidate, normalized_candidate_skills, points_per_skill)
            hard_requirements.append(HardRequirementResult(requirement=req.skill, status=result, evidence=evidence))
            eligibility_points += int(points)
            evidence_total += 1
            if result in {"met", "partial"}:
                evidence_hits += 1

        years_points = 0
        if job.minimum_years_experience is not None:
            candidate_years = candidate.total_years_experience or 0
            ratio = min(1.0, candidate_years / max(1.0, job.minimum_years_experience))
            years_points = int(60 * ratio)
            if ratio < 1:
                hard_requirements.append(
                    HardRequirementResult(
                        requirement=f"Minimum {job.minimum_years_experience} years experience",
                        status="partial" if ratio >= 0.7 else "missing",
                        evidence=f"Detected {candidate_years} years.",
                    )
                )
        else:
            years_points = 45
        eligibility_points += years_points

        tool_points = self._score_tools_platforms(candidate, job)
        eligibility_points += tool_points

        language_location_points = self._score_language_location(candidate, job)
        eligibility_points += language_location_points
        deterministic_breakdown = ScoreBreakdown()
        deterministic_breakdown.eligibility_and_must_have_fit = min(300, eligibility_points)
        deterministic_breakdown.technical_depth = self._score_technical_depth(candidate, job)
        deterministic_breakdown.relevant_professional_experience = self._score_relevant_experience(candidate, job)
        deterministic_breakdown.project_and_achievement_evidence = self._score_projects(candidate, job)
        deterministic_breakdown.seniority_and_ownership = self._score_seniority(candidate)
        deterministic_breakdown.education_and_certifications = self._score_education(candidate, job)
        deterministic_breakdown.communication_and_language = self._score_communication(candidate, job)

        evidence_strength_ratio = evidence_hits / evidence_total if evidence_total else 0.3
        deterministic_breakdown.evidence_confidence = self._score_evidence_confidence(candidate, evidence_strength_ratio)
        breakdown = self._resolve_breakdown(candidate, job, deterministic_breakdown)
        base_total = breakdown.total()

        total_score, cap, strictness_notes, forced_label = self.caps_service.apply_caps(
            base_score=base_total,
            candidate=candidate,
            job=job,
            critical_missing=critical_missing,
            evidence_strength_ratio=evidence_strength_ratio,
        )
        all_critical_met = not critical_missing
        severe_gap = len(critical_missing) > 0 or (job.minimum_years_experience is not None and (candidate.total_years_experience or 0) < job.minimum_years_experience)
        recommendation, confidence = self.recommendation_service.recommend(
            total_score=total_score,
            all_critical_met=all_critical_met,
            extraction_quality=candidate.extraction_quality.quality_level,
            evidence_strength_ratio=evidence_strength_ratio,
            severe_gap=severe_gap,
            forced_label=forced_label,
        )

        strengths, gaps, concerns, evidence_summary = self._derive_reasoning(candidate, job, hard_requirements, critical_missing)
        if cap < 1000:
            strictness_notes.append(f"Score capped at {cap} due to strict cap rules.")
        if not all_critical_met:
            strictness_notes.append("Critical requirements are not fully met.")
        if self.settings.scoring_mode == "llm_hybrid":
            strictness_notes.append("GPT rubric scoring used for category scoring; deterministic caps remained authoritative.")

        return CandidateScoreResult(
            candidate_id=candidate.candidate_id,
            total_score=total_score,
            max_possible_score_after_caps=cap,
            recommendation_label=recommendation,
            confidence_level=confidence,
            score_breakdown=breakdown,
            hard_requirement_results=hard_requirements,
            critical_missing_requirements=critical_missing,
            strengths=strengths,
            gaps=gaps,
            concerns=concerns,
            evidence_summary=evidence_summary,
            interview_questions=[],
            strictness_notes=strictness_notes,
        )

    def _score_candidate_ai_first(self, candidate: CandidateProfile, job: JobRequirementProfile) -> CandidateScoreResult:
        try:
            draft = self.llm_client.score_candidate_structured(candidate, job)
        except Exception:
            return self._score_candidate_deterministic_fallback(candidate, job)

        breakdown = self._sanitize_llm_breakdown(draft, ScoreBreakdown())
        total_score = draft.total_score if draft.total_score is not None else breakdown.total()
        total_score = max(0, min(1000, int(total_score)))
        hard_requirements = draft.hard_requirement_results
        critical_missing = draft.critical_missing_requirements or [
            item.requirement
            for item in hard_requirements
            if item.status == "missing" and any(item.requirement.lower() == requirement.skill.lower() for requirement in job.critical_skills)
        ]
        recommendation = draft.recommendation_label or "Needs Recruiter Review"
        confidence = draft.confidence_level or "Medium"
        strictness_notes = list(draft.strictness_notes)
        strictness_notes.append("AI-first evaluation used; deterministic scoring is disabled unless AI evaluation fails.")
        if candidate.extraction_quality and candidate.extraction_quality.quality_level in {"low", "failed"}:
            strictness_notes.append("Extraction quality is weak; review the original document before relying on this evaluation.")
            confidence = "Low"

        return CandidateScoreResult(
            candidate_id=candidate.candidate_id,
            total_score=total_score,
            max_possible_score_after_caps=1000,
            recommendation_label=recommendation,
            confidence_level=confidence,
            score_breakdown=breakdown,
            hard_requirement_results=hard_requirements,
            critical_missing_requirements=critical_missing,
            strengths=draft.strengths,
            gaps=draft.gaps,
            concerns=draft.concerns,
            evidence_summary=draft.evidence_summary,
            interview_questions=[],
            strictness_notes=strictness_notes,
        )

    def _score_candidate_deterministic_fallback(self, candidate: CandidateProfile, job: JobRequirementProfile) -> CandidateScoreResult:
        original_mode = self.settings.scoring_mode
        self.settings.scoring_mode = "deterministic"
        try:
            result = self.score_candidate(candidate, job)
        finally:
            self.settings.scoring_mode = original_mode
        result.strictness_notes.append("AI evaluation failed; deterministic fallback was used.")
        return result

    def _resolve_breakdown(
        self,
        candidate: CandidateProfile,
        job: JobRequirementProfile,
        deterministic_breakdown: ScoreBreakdown,
    ) -> ScoreBreakdown:
        if self.settings.scoring_mode != "llm_hybrid" or not self.llm_client:
            return deterministic_breakdown
        draft = self.llm_client.score_candidate_structured(candidate, job)
        return self._sanitize_llm_breakdown(draft, deterministic_breakdown)

    def _sanitize_llm_breakdown(
        self, draft: LLMScoreAssessment, fallback: ScoreBreakdown
    ) -> ScoreBreakdown:
        values = draft.score_breakdown.model_dump()
        fallback_values = fallback.model_dump()
        clean: dict[str, int] = {}
        for field_name, maximum in self.CATEGORY_MAXIMA.items():
            raw_value = values.get(field_name, fallback_values[field_name])
            try:
                parsed = int(raw_value)
            except (TypeError, ValueError):
                parsed = fallback_values[field_name]
            clean[field_name] = max(0, min(maximum, parsed))
        return ScoreBreakdown(**clean)

    def _score_skill_requirement(
        self,
        req: SkillRequirement,
        candidate: CandidateProfile,
        normalized_candidate_skills: list[str],
        max_points: float,
    ) -> tuple[str, float, str]:
        normalized_req = self.skill_normalizer.normalize(req.skill)
        normalized_synonyms = [self.skill_normalizer.normalize(s) for s in req.synonyms]
        haystack = normalized_candidate_skills + normalized_synonyms

        if normalized_req in normalized_candidate_skills:
            evidence = self._find_evidence(candidate, normalized_req, normalized_synonyms)
            if evidence == "work":
                return "met", max_points, "Explicit work evidence."
            if evidence == "project":
                return "met", max_points * 0.9, "Explicit project evidence."
            if evidence == "language":
                return "met", max_points * 0.9, "Explicit language evidence."
            if evidence == "skills":
                return "partial", max_points * 0.6, "Skill listed in skills section."
            if evidence == "implied":
                return "partial", max_points * 0.4, "Implied evidence."
            return "partial", max_points * 0.4, "Implied evidence."
        evidence = self._find_evidence(candidate, normalized_req, normalized_synonyms)
        if evidence == "work":
            return "met", max_points * 0.85, "Relevant work evidence."
        if evidence == "project":
            return "met", max_points * 0.75, "Relevant project evidence."
        if evidence == "language":
            return "partial", max_points * 0.7, "Language evidence."
        if evidence == "skills":
            return "partial", max_points * 0.55, "Related skill evidence."
        if evidence == "implied":
            return "partial", max_points * 0.35, "Contextual evidence."
        match_score = self.semantic_matcher.best_match_score(normalized_req, haystack)
        if match_score >= 0.85:
            return "partial", max_points * 0.35, "Semantic partial match."
        return "missing", 0.0, "No evidence."

    def _find_evidence(self, candidate: CandidateProfile, skill: str, synonyms: list[str] | None = None) -> str:
        search_terms = [skill] + (synonyms or [])
        normalized_terms = [lower_no_punct(term) for term in search_terms if term]
        for exp in candidate.work_experience:
            joined = " ".join(exp.technologies + exp.responsibilities + exp.achievements).lower()
            normalized_joined = lower_no_punct(joined)
            if any(term and term in normalized_joined for term in normalized_terms):
                return "work"
        for proj in candidate.projects:
            joined = " ".join(proj.technologies + [proj.description or "", proj.business_impact or ""]).lower()
            normalized_joined = lower_no_punct(joined)
            if any(term and term in normalized_joined for term in normalized_terms):
                return "project"
        candidate_skill_terms = [lower_no_punct(s) for s in candidate.skills.all_skills()]
        if any(term and term in candidate_skill_terms for term in normalized_terms):
            return "skills"
        language_terms = [lower_no_punct(language) for language in candidate.languages]
        if any(term and any(term in language for language in language_terms) for term in normalized_terms):
            return "language"
        if self._has_contextual_requirement_match(candidate, normalized_terms):
            return "implied"
        return "none"

    def _has_contextual_requirement_match(self, candidate: CandidateProfile, normalized_terms: list[str]) -> bool:
        candidate_blob = lower_no_punct(
            " ".join(
                candidate.skills.all_skills()
                + candidate.languages
                + [candidate.summary or "", candidate.location or ""]
                + [item.role or "" for item in candidate.work_experience]
                + [item.company or "" for item in candidate.work_experience]
                + [text for item in candidate.work_experience for text in item.responsibilities + item.technologies + item.achievements]
                + [text for item in candidate.projects for text in item.technologies + [item.description or "", item.business_impact or ""]]
            )
        )
        for term in normalized_terms:
            if term and term in candidate_blob:
                return True
            tokens = [
                token
                for token in term.split()
                if len(token) > 2 and token not in self.REQUIREMENT_STOPWORDS
            ]
            if tokens and any(token in candidate_blob for token in tokens):
                return True
        return False

    @staticmethod
    def _score_tools_platforms(candidate: CandidateProfile, job: JobRequirementProfile) -> int:
        if not job.tools_and_platforms:
            return 28
        candidate_blob = " ".join(candidate.skills.all_skills()).lower()
        hits = sum(1 for item in job.tools_and_platforms if item.lower() in candidate_blob)
        return int(40 * (hits / max(1, len(job.tools_and_platforms))))

    @staticmethod
    def _score_language_location(candidate: CandidateProfile, job: JobRequirementProfile) -> int:
        if not job.required_languages and not job.location_requirements:
            return 18
        score = 0
        if job.required_languages:
            if any(req.lower() in " ".join(candidate.languages).lower() for req in job.required_languages):
                score += 14
        else:
            score += 8
        if job.location_requirements:
            if candidate.location and any(req.lower() in candidate.location.lower() for req in job.location_requirements):
                score += 6
        else:
            score += 6
        return score

    def _score_technical_depth(self, candidate: CandidateProfile, job: JobRequirementProfile) -> int:
        primary = min(120, len(candidate.skills.programming_languages + candidate.skills.frameworks + candidate.skills.ai_ml) * 12)
        secondary = min(50, len(candidate.skills.cloud + candidate.skills.databases + candidate.skills.devops) * 6)
        architecture = 40 if any("architecture" in (item.description or "").lower() for item in candidate.projects) else 18
        devops = min(40, len(candidate.skills.devops + candidate.skills.cloud + candidate.skills.databases) * 5)
        return min(250, primary + secondary + architecture + devops)

    @staticmethod
    def _score_relevant_experience(candidate: CandidateProfile, job: JobRequirementProfile) -> int:
        role_sim = 50 if candidate.work_experience else 10
        resp = min(50, sum(len(exp.responsibilities) for exp in candidate.work_experience) * 4)
        ownership = 40 if any(exp.achievements for exp in candidate.work_experience) else 18
        domain = 20 if any(domain.lower() in (candidate.summary or "").lower() for domain in job.domain_preferences) else 8
        return min(180, role_sim + resp + ownership + domain)

    @staticmethod
    def _score_projects(candidate: CandidateProfile, job: JobRequirementProfile) -> int:
        relevant_projects = min(50, len(candidate.projects) * 16)
        measurable = min(30, sum(1 for proj in candidate.projects if proj.business_impact) * 10)
        complexity = min(20, sum(len(proj.technologies) for proj in candidate.projects) * 2)
        return min(100, relevant_projects + measurable + complexity)

    @staticmethod
    def _score_seniority(candidate: CandidateProfile) -> int:
        years = candidate.total_years_experience or 0
        leadership = 30 if years >= 8 else 20 if years >= 5 else 10
        decision = 20 if any("led" in " ".join(exp.responsibilities).lower() for exp in candidate.work_experience) else 10
        cross_func = 20 if any("stakeholder" in " ".join(exp.responsibilities).lower() for exp in candidate.work_experience) else 8
        return min(70, leadership + decision + cross_func)

    @staticmethod
    def _score_education(candidate: CandidateProfile, job: JobRequirementProfile) -> int:
        edu_points = 20 if candidate.education else 8
        cert_points = min(20, len(candidate.certifications) * 8) if job.required_certifications or job.preferred_certifications else min(20, len(candidate.certifications) * 5)
        return min(40, edu_points + cert_points)

    @staticmethod
    def _score_communication(candidate: CandidateProfile, job: JobRequirementProfile) -> int:
        language = 20 if (not job.required_languages or any(req.lower() in " ".join(candidate.languages).lower() for req in job.required_languages)) else 8
        clarity = 10 if candidate.extraction_quality.text_length > 1000 else 5
        return min(30, language + clarity)

    @staticmethod
    def _score_evidence_confidence(candidate: CandidateProfile, evidence_ratio: float) -> int:
        evidence_points = int(20 * evidence_ratio)
        extraction_points = int(10 * (candidate.extraction_quality.score / 100))
        return min(30, evidence_points + extraction_points)

    @staticmethod
    def _derive_reasoning(
        candidate: CandidateProfile,
        job: JobRequirementProfile,
        requirements: list[HardRequirementResult],
        critical_missing: list[str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        met = [r.requirement for r in requirements if r.status == "met"][:6]
        missing = [r.requirement for r in requirements if r.status == "missing"][:6]
        strengths = [f"Clear evidence for {req}." for req in met] or ["Basic profile extracted."]
        gaps = [f"Missing or weak evidence for {req}." for req in missing]
        if (candidate.total_years_experience or 0) < (job.minimum_years_experience or 0):
            gaps.append("Experience below minimum requirement.")
        concerns = []
        if critical_missing:
            concerns.append(f"Critical missing requirements: {', '.join(critical_missing)}.")
        if candidate.extraction_quality.quality_level in {"low", "failed"}:
            concerns.append("Low extraction quality; manual validation required.")
        evidence_summary = [item.source_text for item in candidate.raw_evidence[:10]]
        return strengths[:8], gaps[:8], concerns[:8], evidence_summary
