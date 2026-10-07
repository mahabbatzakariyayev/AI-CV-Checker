import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db_models import Candidate, CandidateScore, ScreeningJob, UploadedFile
from app.schemas.candidate import CandidateProfile
from app.services.document_extraction.extraction_quality_service import ExtractionQualityService
from app.services.document_extraction.service import DocumentExtractionService
from app.services.file_validation_service import FileValidationService
from app.services.llm.agentic_evaluation_service import AgenticEvaluationService
from app.services.llm.factory import get_llm_client
from app.services.llm.mock_llm_client import MockLLMClient
from app.services.parsing.candidate_profile_service import CandidateProfileService
from app.services.parsing.job_requirement_service import JobRequirementService
from app.services.scoring.scoring_engine import ScoringEngine
from app.services.zip_service import ZipService, ZipServiceError
from app.utils.logging import log_event, log_exception_event


class ScreeningPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.zip_service = ZipService()
        self.file_validator = FileValidationService()
        self.extractor = DocumentExtractionService()
        self.quality_service = ExtractionQualityService()
        self.llm_client = get_llm_client()
        self.job_service = JobRequirementService(self.llm_client)
        self.candidate_service = CandidateProfileService(self.llm_client)
        self.scoring_engine = ScoringEngine(self.llm_client)
        self.agentic_evaluator = AgenticEvaluationService(self.llm_client)

    def analyze_screening_job(self, job_id: str) -> None:
        job = self.db.query(ScreeningJob).filter(ScreeningJob.id == job_id).first()
        if not job:
            raise ValueError("Screening job not found")
        if not job.job_requirement_text and not job.job_requirement_file_path:
            raise ValueError("Job requirement missing")
        if not job.cv_zip_path:
            raise ValueError("CV ZIP missing")

        job.status = "processing"
        self.db.commit()
        log_event(self.db, job.id, "Analysis started.")

        try:
            job_text = self._read_job_requirement(job)
            log_event(self.db, job.id, "Job requirement text extracted.", details={"length": len(job_text)})
            try:
                job_profile = self.job_service.parse(job_text)
                log_event(self.db, job.id, "Job requirement parsed with primary LLM parser.", details={"parser_mode": "primary_llm"})
                self._log_llm_traces(job.id, step_key="job_requirement_llm")
            except Exception as parse_exc:
                log_exception_event(
                    self.db,
                    job.id,
                    "Primary job requirement parsing failed; falling back to mock parser.",
                    parse_exc,
                )
                fallback_llm = MockLLMClient()
                job_profile = fallback_llm.extract_job_requirement(job_text)
                log_event(self.db, job.id, "Job requirement parsed with fallback mock parser.", details={"parser_mode": "mock_fallback"})
                self._log_llm_traces(job.id, step_key="job_requirement_llm", llm_client=fallback_llm)
            job.job_requirement_json = job_profile.model_dump_json()
            log_event(
                self.db,
                job.id,
                "Job requirement structured output saved.",
                details={"step_key": "job_requirement_structured", "job_requirement_preview": self._truncate_data(job_profile.model_dump(mode="json"), max_chars=6000)},
            )
            self.db.commit()
            log_event(self.db, job.id, "Job requirement parsed.")
        except Exception as exc:
            job.status = "failed"
            self.db.commit()
            log_exception_event(self.db, job.id, "Job requirement parsing failed.", exc)
            raise

        extraction_dir = Path(self.settings.upload_dir) / job.id / "cvs_extracted"
        try:
            cv_files = self.zip_service.extract_cv_zip(Path(job.cv_zip_path), extraction_dir)
            log_event(self.db, job.id, f"{len(cv_files)} files extracted from ZIP.")
        except ZipServiceError as exc:
            job.status = "failed"
            self.db.commit()
            log_exception_event(self.db, job.id, "ZIP extraction failed.", exc)
            raise

        for file_path in cv_files:
            uploaded = UploadedFile(
                screening_job_id=job.id,
                original_file_name=file_path.name,
                stored_file_path=str(file_path),
                file_type=file_path.suffix.lower().lstrip("."),
                file_size=file_path.stat().st_size if file_path.exists() else 0,
                status="processing",
            )
            self.db.add(uploaded)
            self.db.commit()
            self.db.refresh(uploaded)
            log_event(self.db, job.id, f"{file_path.name} extraction started.")

            try:
                self.file_validator.validate_cv_file(file_path)
                extracted = self.extractor.extract(file_path)
                log_event(
                    self.db,
                    job.id,
                    f"{file_path.name} extraction finished.",
                    details={
                        "step_key": "document_extracted",
                        "extraction_method": extracted.extraction_method,
                        "page_count": extracted.page_count,
                        "text_length": len(extracted.full_text or ""),
                        "document_preview": self._build_document_preview(extracted),
                    },
                )
                quality = self.quality_service.evaluate(extracted)
                extracted.extraction_quality = quality
                log_event(
                    self.db,
                    job.id,
                    f"{file_path.name} extraction quality evaluated.",
                    details={
                        "step_key": "document_quality",
                        "quality_level": quality.quality_level,
                        "quality_score": quality.score,
                        "warnings": quality.warnings,
                        "requires_manual_review": quality.requires_manual_review,
                    },
                )
                candidate_id = str(uuid4())
                try:
                    profile: CandidateProfile = self.candidate_service.extract_profile(candidate_id, uploaded.id, extracted)
                    log_event(
                        self.db,
                        job.id,
                        f"{file_path.name} candidate profile parsed with primary LLM parser.",
                        details={"parser_mode": "primary_llm"},
                        candidate_id=candidate_id,
                    )
                    self._log_llm_traces(job.id, candidate_id=candidate_id, step_key="candidate_profile_llm")
                except Exception as profile_exc:
                    log_exception_event(
                        self.db,
                        job.id,
                        f"{file_path.name} candidate extraction via primary LLM failed; falling back to mock parser.",
                        profile_exc,
                        candidate_id=candidate_id,
                    )
                    fallback_llm = MockLLMClient()
                    profile = fallback_llm.extract_candidate_profile(candidate_id, uploaded.id, extracted)
                    log_event(
                        self.db,
                        job.id,
                        f"{file_path.name} candidate profile parsed with fallback mock parser.",
                        details={"parser_mode": "mock_fallback"},
                        candidate_id=candidate_id,
                    )
                    self._log_llm_traces(job.id, candidate_id=candidate_id, step_key="candidate_profile_llm", llm_client=fallback_llm)
                if profile.extraction_quality is None:
                    profile = profile.model_copy(update={"extraction_quality": quality})
                log_event(
                    self.db,
                    job.id,
                    f"{file_path.name} candidate profile structured.",
                    details={"step_key": "candidate_profile_structured", "candidate_profile_preview": self._build_candidate_profile_preview(profile)},
                    candidate_id=profile.candidate_id,
                )
                score = self.scoring_engine.score_candidate(profile, job_profile)
                self._log_llm_traces(job.id, candidate_id=profile.candidate_id, step_key="scoring_llm")
                log_event(
                    self.db,
                    job.id,
                    f"{file_path.name} scoring completed.",
                    details={
                        "step_key": "ai_scoring_evaluation" if self.settings.scoring_mode == "llm_first" else "deterministic_scoring",
                        "scoring_mode": self.settings.scoring_mode,
                        "total_score": score.total_score,
                        "max_after_caps": score.max_possible_score_after_caps,
                        "recommendation": score.recommendation_label,
                        "breakdown": score.score_breakdown.model_dump(mode="json"),
                        "critical_missing_requirements": score.critical_missing_requirements,
                    },
                    candidate_id=profile.candidate_id,
                )
                explanation, questions = self.agentic_evaluator.run(profile, job_profile, score)
                self._log_llm_traces(job.id, candidate_id=profile.candidate_id, step_key="agentic_explanation_llm")
                log_event(
                    self.db,
                    job.id,
                    f"{file_path.name} agentic explanation completed.",
                    details={
                        "step_key": "agentic_explanation_result",
                        "questions_count": len(questions),
                        "agentic": True,
                        "explanation_preview": self._truncate_data(explanation, max_chars=6000),
                        "questions_preview": questions[:8],
                    },
                    candidate_id=profile.candidate_id,
                )
                score.strengths = explanation.get("strengths", score.strengths)
                score.gaps = explanation.get("gaps", score.gaps)
                score.concerns = explanation.get("concerns", score.concerns)
                score.evidence_summary = explanation.get("evidence_summary", score.evidence_summary)
                score.strictness_notes = explanation.get("strictness_notes", score.strictness_notes)
                score.interview_questions = questions or score.interview_questions

                candidate_record = Candidate(
                    id=profile.candidate_id,
                    screening_job_id=job.id,
                    uploaded_file_id=uploaded.id,
                    candidate_name=profile.candidate_name,
                    email=profile.email,
                    phone=profile.phone,
                    location=profile.location,
                    total_years_experience=profile.total_years_experience,
                    candidate_json=profile.model_dump_json(),
                    extraction_quality_json=quality.model_dump_json(),
                    status="processed",
                )
                self.db.add(candidate_record)
                self.db.commit()

                score_record = CandidateScore(
                    screening_job_id=job.id,
                    candidate_id=profile.candidate_id,
                    total_score=score.total_score,
                    max_possible_score_after_caps=score.max_possible_score_after_caps,
                    recommendation_label=score.recommendation_label,
                    confidence_level=score.confidence_level,
                    score_breakdown_json=score.score_breakdown.model_dump_json(),
                    hard_requirements_json=json.dumps([item.model_dump() for item in score.hard_requirement_results]),
                    strengths_json=json.dumps(score.strengths),
                    gaps_json=json.dumps(score.gaps),
                    concerns_json=json.dumps(score.concerns),
                    evidence_json=json.dumps([item.model_dump() for item in profile.raw_evidence[:30]]),
                    interview_questions_json=json.dumps(score.interview_questions),
                    strictness_notes_json=json.dumps(score.strictness_notes),
                )
                self.db.add(score_record)
                uploaded.status = "processed"
                self.db.commit()
                log_event(self.db, job.id, f"{file_path.name} processed successfully.", details={"score": score.total_score}, candidate_id=profile.candidate_id)
            except Exception as exc:
                uploaded.status = "failed"
                uploaded.error_message = str(exc)
                self.db.commit()
                log_exception_event(
                    self.db,
                    job.id,
                    f"{file_path.name} failed.",
                    exc,
                    candidate_id=candidate_id if "candidate_id" in locals() else None,
                )
                continue

        job.status = "completed"
        self.db.commit()
        log_event(self.db, job.id, "Analysis completed.")

    def _read_job_requirement(self, job: ScreeningJob) -> str:
        if job.job_requirement_text:
            return job.job_requirement_text
        path = Path(job.job_requirement_file_path or "")
        self.file_validator.validate_job_file(path)
        extracted = self.extractor.extract(path)
        return extracted.full_text

    def _log_llm_traces(
        self,
        job_id: str,
        *,
        step_key: str,
        candidate_id: str | None = None,
        llm_client=None,
    ) -> None:
        client = llm_client or self.llm_client
        traces = client.drain_debug_traces() if client else []
        for trace in traces:
            log_event(
                self.db,
                job_id,
                "LLM trace captured.",
                details={"step_key": step_key, "trace": self._truncate_data(trace, max_chars=7000)},
                candidate_id=candidate_id,
            )

    def _build_document_preview(self, extracted) -> dict:
        pages = [
            {
                "page_number": page.page_number,
                "confidence": page.confidence,
                "text_preview": self._truncate_data(page.text or "", max_chars=800),
            }
            for page in extracted.pages[:5]
        ]
        return {
            "file_name": extracted.file_name,
            "file_type": extracted.file_type,
            "page_count": extracted.page_count,
            "extraction_method": extracted.extraction_method,
            "detected_sections": extracted.detected_sections[:20],
            "warnings": extracted.warnings[:20],
            "tables_count": len(extracted.tables),
            "full_text_preview": self._truncate_data(extracted.full_text or "", max_chars=5000),
            "pages_preview": pages,
        }

    def _build_candidate_profile_preview(self, profile: CandidateProfile) -> dict:
        return {
            "candidate_id": profile.candidate_id,
            "candidate_name": profile.candidate_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "total_years_experience": profile.total_years_experience,
            "skills": profile.skills.model_dump(mode="json"),
            "work_experience_count": len(profile.work_experience),
            "projects_count": len(profile.projects),
            "certifications_count": len(profile.certifications),
            "languages": profile.languages,
            "raw_evidence_count": len(profile.raw_evidence),
            "raw_evidence_preview": [item.model_dump(mode="json") for item in profile.raw_evidence[:10]],
        }

    @staticmethod
    def _truncate_data(value, *, max_chars: int = 4000):
        if isinstance(value, str):
            text = value
        else:
            text = json.dumps(value, ensure_ascii=False, default=str)
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars]}... [truncated {len(text) - max_chars} chars]"
