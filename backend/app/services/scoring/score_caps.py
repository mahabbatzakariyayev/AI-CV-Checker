from app.schemas.candidate import CandidateProfile
from app.schemas.extraction import ExtractionQuality
from app.schemas.job_requirement import JobRequirementProfile


class ScoreCapsService:
    def apply_caps(
        self,
        base_score: int,
        candidate: CandidateProfile,
        job: JobRequirementProfile,
        critical_missing: list[str],
        evidence_strength_ratio: float,
    ) -> tuple[int, int, list[str], str | None]:
        cap = 1000
        notes: list[str] = []
        forced_label: str | None = None
        extraction_quality: ExtractionQuality = candidate.extraction_quality

        if extraction_quality.quality_level == "failed":
            return 0, 0, ["Candidate profile extraction failed."], "Failed Extraction"
        if extraction_quality.quality_level == "low":
            cap = min(cap, 649)
            notes.append("Extraction quality is low; cap applied at 649.")
        if len(critical_missing) >= 2:
            cap = min(cap, 649)
            notes.append("Two or more critical skills missing; cap applied at 649.")
        elif len(critical_missing) == 1:
            cap = min(cap, 749)
            notes.append("One critical skill missing; cap applied at 749.")

        if job.minimum_years_experience and (candidate.total_years_experience or 0) < job.minimum_years_experience:
            cap = min(cap, 699)
            notes.append("Minimum years of experience not met; cap applied at 699.")
        if job.required_languages and not any(
            language.lower() in " ".join(candidate.languages).lower() for language in job.required_languages
        ):
            cap = min(cap, 799)
            notes.append("Required language not clearly evidenced; cap applied at 799.")
        if evidence_strength_ratio < 0.45:
            cap = min(cap, 749)
            notes.append("Evidence quality low; cap applied at 749.")
        if candidate.skills.all_skills() and not candidate.work_experience and not candidate.projects:
            cap = min(cap, 779)
            notes.append("Skills listed without work/project proof; cap applied at 779.")
        if not candidate.work_experience and not candidate.projects:
            cap = min(cap, 749)
            notes.append("Main role alignment not clearly proven; cap applied at 749.")

        return min(base_score, cap), cap, notes, forced_label
