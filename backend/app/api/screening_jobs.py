import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.models.db_models import Candidate, CandidateScore, ProcessingLog, ScreeningJob, UploadedFile
from app.schemas.screening import (
    CreateScreeningJobRequest,
    JobRequirementTextRequest,
    ScreeningJobResponse,
    ScreeningStatusResponse,
)
from app.services.worker.analysis_worker import analysis_worker


router = APIRouter(prefix="/api/screening-jobs", tags=["screening-jobs"])


@router.get("")
def list_screening_jobs(db: Session = Depends(get_db)) -> list[dict]:
    jobs = db.query(ScreeningJob).order_by(ScreeningJob.created_at.desc()).all()
    results: list[dict] = []
    for job in jobs:
        total_files = db.query(UploadedFile).filter(UploadedFile.screening_job_id == job.id).count()
        processed = db.query(UploadedFile).filter(
            UploadedFile.screening_job_id == job.id, UploadedFile.status == "processed"
        ).count()
        failed = db.query(UploadedFile).filter(
            UploadedFile.screening_job_id == job.id, UploadedFile.status == "failed"
        ).count()
        results.append(
            {
                "id": job.id,
                "title": job.title,
                "status": job.status,
                "submitted_at": job.created_at.isoformat(),
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
                "total_files": total_files,
                "processed_files": processed,
                "failed_files": failed,
                "job_parser_mode": _detect_job_parser_mode(db, job.id),
                "analysis_duration_seconds": _get_job_analysis_duration_seconds(db, job.id),
                "last_event": _get_last_job_event(db, job.id),
            }
        )
    return results


@router.post("", response_model=ScreeningJobResponse)
def create_screening_job(payload: CreateScreeningJobRequest, db: Session = Depends(get_db)) -> ScreeningJobResponse:
    job = ScreeningJob(title=payload.title, status="created")
    db.add(job)
    db.commit()
    db.refresh(job)
    return ScreeningJobResponse(id=job.id, title=job.title, status=job.status)


@router.post("/{job_id}/job-requirement/text")
def set_job_requirement_text(job_id: str, payload: JobRequirementTextRequest, db: Session = Depends(get_db)) -> dict:
    job = _get_job_or_404(db, job_id)
    job.job_requirement_text = payload.text
    job.status = "job_requirement_ready"
    db.commit()
    return {"job_id": job.id, "status": job.status}


@router.post("/{job_id}/job-requirement/file")
def upload_job_requirement_file(job_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    job = _get_job_or_404(db, job_id)
    settings = get_settings()
    folder = Path(settings.upload_dir) / job_id / "job_requirement"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / file.filename
    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    job.job_requirement_file_path = str(target)
    job.status = "job_requirement_ready"
    db.commit()
    return {"job_id": job.id, "status": job.status, "file_path": str(target)}


@router.post("/{job_id}/upload-cvs")
def upload_cvs_zip(job_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    job = _get_job_or_404(db, job_id)
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported.")
    settings = get_settings()
    folder = Path(settings.upload_dir) / job_id
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / file.filename
    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    job.cv_zip_path = str(target)
    job.status = "cv_zip_uploaded"
    db.commit()
    return {"job_id": job.id, "status": job.status, "file_path": str(target)}


@router.post("/{job_id}/analyze")
def analyze_screening_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = _get_job_or_404(db, job_id)
    if not job.job_requirement_text and not job.job_requirement_file_path:
        raise HTTPException(status_code=400, detail="Job requirement missing")
    if not job.cv_zip_path:
        raise HTTPException(status_code=400, detail="CV ZIP missing")
    try:
        return analysis_worker.enqueue(job.id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{job_id}/status", response_model=ScreeningStatusResponse)
def get_screening_status(job_id: str, db: Session = Depends(get_db)) -> ScreeningStatusResponse:
    job = _get_job_or_404(db, job_id)
    total_files = db.query(UploadedFile).filter(UploadedFile.screening_job_id == job.id).count()
    processed = db.query(UploadedFile).filter(UploadedFile.screening_job_id == job.id, UploadedFile.status == "processed").count()
    failed = db.query(UploadedFile).filter(UploadedFile.screening_job_id == job.id, UploadedFile.status == "failed").count()
    errors = [
        f"{item.original_file_name}: {item.error_message}"
        for item in db.query(UploadedFile).filter(UploadedFile.screening_job_id == job.id, UploadedFile.status == "failed").all()
    ]
    return ScreeningStatusResponse(
        job_id=job.id,
        status=job.status,
        total_files=total_files,
        processed_files=processed,
        failed_files=failed,
        created_at=job.created_at,
        updated_at=job.updated_at,
        errors=errors,
    )


@router.get("/{job_id}/candidates")
def get_ranked_candidates(job_id: str, db: Session = Depends(get_db)) -> list[dict]:
    _get_job_or_404(db, job_id)
    rows = (
        db.query(Candidate, CandidateScore, UploadedFile)
        .join(CandidateScore, CandidateScore.candidate_id == Candidate.id)
        .join(UploadedFile, UploadedFile.id == Candidate.uploaded_file_id)
        .filter(Candidate.screening_job_id == job_id)
        .order_by(CandidateScore.total_score.desc())
        .all()
    )
    results = []
    for idx, (candidate, score, file) in enumerate(rows, start=1):
        quality = json.loads(candidate.extraction_quality_json)
        results.append(
            {
                "rank": idx,
                "candidate_id": candidate.id,
                "candidate_name": candidate.candidate_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "score": score.total_score,
                "max_score_after_caps": score.max_possible_score_after_caps,
                "recommendation": score.recommendation_label,
                "confidence": score.confidence_level,
                "years_experience": candidate.total_years_experience,
                "candidate_created_at": candidate.created_at.isoformat(),
                "score_created_at": score.created_at.isoformat(),
                "strengths": json.loads(score.strengths_json),
                "gaps": json.loads(score.gaps_json),
                "extraction_quality": quality,
                "original_file_name": file.original_file_name,
                "parser_mode": _detect_candidate_parser_mode(db, job_id, candidate.id),
                "scoring_mode": _scoring_mode_id(),
                "ai_usage": {
                    "job_requirement_parser": _detect_job_parser_mode(db, job_id),
                    "candidate_parser": _detect_candidate_parser_mode(db, job_id, candidate.id),
                    "scoring_engine": _scoring_engine_id(),
                    "explanation_engine": "langgraph_agentic",
                },
            }
        )
    return results


@router.get("/{job_id}/candidates/{candidate_id}")
def get_candidate_details(job_id: str, candidate_id: str, db: Session = Depends(get_db)) -> dict:
    _get_job_or_404(db, job_id)
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.screening_job_id == job_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    score = db.query(CandidateScore).filter(CandidateScore.candidate_id == candidate.id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Candidate score not found")
    job_parser_mode = _detect_job_parser_mode(db, job_id)
    candidate_parser_mode = _detect_candidate_parser_mode(db, job_id, candidate.id)
    return {
        "candidate": json.loads(candidate.candidate_json),
        "parser_mode": candidate_parser_mode,
        "scoring_mode": _scoring_mode_id(),
        "ai_usage": {
            "job_requirement_parser": job_parser_mode,
            "candidate_parser": candidate_parser_mode,
            "scoring_engine": _scoring_engine_id(),
            "explanation_engine": "langgraph_agentic",
        },
        "extraction_quality": json.loads(candidate.extraction_quality_json),
        "score": {
            "total_score": score.total_score,
            "max_possible_score_after_caps": score.max_possible_score_after_caps,
            "recommendation_label": score.recommendation_label,
            "confidence_level": score.confidence_level,
            "score_breakdown": json.loads(score.score_breakdown_json),
            "hard_requirements": json.loads(score.hard_requirements_json),
            "strengths": json.loads(score.strengths_json),
            "gaps": json.loads(score.gaps_json),
            "concerns": json.loads(score.concerns_json),
            "evidence": json.loads(score.evidence_json),
            "interview_questions": json.loads(score.interview_questions_json),
            "strictness_notes": json.loads(score.strictness_notes_json),
        },
    }


@router.get("/{job_id}/candidates/{candidate_id}/trace")
def get_candidate_trace(job_id: str, candidate_id: str, db: Session = Depends(get_db)) -> dict:
    _get_job_or_404(db, job_id)
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.screening_job_id == job_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    score = db.query(CandidateScore).filter(CandidateScore.candidate_id == candidate.id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Candidate score not found")

    job_parser_mode = _detect_job_parser_mode(db, job_id)
    candidate_parser_mode = _detect_candidate_parser_mode(db, job_id, candidate.id)
    logs = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.screening_job_id == job_id,
            (ProcessingLog.candidate_id == candidate_id) | (ProcessingLog.candidate_id.is_(None)),
        )
        .order_by(ProcessingLog.created_at.asc())
        .all()
    )
    steps: list[dict] = []
    for item in logs:
        details = json.loads(item.details_json or "{}")
        steps.append(
            {
                "id": item.id,
                "timestamp": item.created_at.isoformat(),
                "level": item.level,
                "message": item.message,
                "candidate_id": item.candidate_id,
                "step_key": details.get("step_key"),
                "details": details,
            }
        )
    return {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "parser_mode": candidate_parser_mode,
        "scoring_mode": _scoring_mode_id(),
        "ai_usage": {
            "job_requirement_parser": job_parser_mode,
            "candidate_parser": candidate_parser_mode,
            "scoring_engine": _scoring_engine_id(),
            "explanation_engine": "langgraph_agentic",
        },
        "candidate_profile": json.loads(candidate.candidate_json),
        "extraction_quality": json.loads(candidate.extraction_quality_json),
        "score": {
            "total_score": score.total_score,
            "max_possible_score_after_caps": score.max_possible_score_after_caps,
            "recommendation_label": score.recommendation_label,
            "confidence_level": score.confidence_level,
            "score_breakdown": json.loads(score.score_breakdown_json),
            "hard_requirements": json.loads(score.hard_requirements_json),
            "strengths": json.loads(score.strengths_json),
            "gaps": json.loads(score.gaps_json),
            "concerns": json.loads(score.concerns_json),
            "evidence": json.loads(score.evidence_json),
            "interview_questions": json.loads(score.interview_questions_json),
            "strictness_notes": json.loads(score.strictness_notes_json),
        },
        "steps": steps,
    }


@router.get("/{job_id}/logs")
def get_processing_logs(job_id: str, db: Session = Depends(get_db)) -> list[dict]:
    _get_job_or_404(db, job_id)
    logs = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.screening_job_id == job_id)
        .order_by(ProcessingLog.created_at.asc())
        .all()
    )
    return [
        {
            "id": item.id,
            "level": item.level,
            "message": item.message,
            "details": json.loads(item.details_json or "{}"),
            "created_at": item.created_at.isoformat(),
            "candidate_id": item.candidate_id,
        }
        for item in logs
    ]


@router.get("/{job_id}/diagnostics")
def get_job_diagnostics(job_id: str, db: Session = Depends(get_db)) -> dict:
    _get_job_or_404(db, job_id)
    job_parser_mode = _detect_job_parser_mode(db, job_id)
    rows = (
        db.query(Candidate.id)
        .filter(Candidate.screening_job_id == job_id)
        .all()
    )
    candidate_ids = [item[0] for item in rows]
    candidate_modes = {candidate_id: _detect_candidate_parser_mode(db, job_id, candidate_id) for candidate_id in candidate_ids}
    fallback_count = sum(1 for mode in candidate_modes.values() if mode == "mock_fallback")
    primary_count = sum(1 for mode in candidate_modes.values() if mode == "primary_llm")
    return {
        "job_id": job_id,
        "job_parser_mode": job_parser_mode,
        "candidate_parser_modes": candidate_modes,
        "candidate_primary_llm_count": primary_count,
        "candidate_mock_fallback_count": fallback_count,
        "scoring_mode": _scoring_mode_id(),
        "scoring_engine": _scoring_engine_id(),
        "explanation_engine": "langgraph_agentic",
    }


@router.get("/{job_id}/status/stream")
async def stream_screening_status(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    _get_job_or_404(db, job_id)
    settings = get_settings()

    async def event_generator():
        while True:
            with SessionLocal() as stream_db:
                job = _get_job_or_404(stream_db, job_id)
                total_files = stream_db.query(UploadedFile).filter(UploadedFile.screening_job_id == job.id).count()
                processed = stream_db.query(UploadedFile).filter(
                    UploadedFile.screening_job_id == job.id, UploadedFile.status == "processed"
                ).count()
                failed = stream_db.query(UploadedFile).filter(
                    UploadedFile.screening_job_id == job.id, UploadedFile.status == "failed"
                ).count()
                payload = {
                    "job_id": job.id,
                    "status": job.status,
                    "total_files": total_files,
                    "processed_files": processed,
                    "failed_files": failed,
                    "is_active": analysis_worker.is_active(job.id),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                if job.status in {"completed", "failed"}:
                    break
            await asyncio.sleep(settings.status_stream_interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _get_job_or_404(db: Session, job_id: str) -> ScreeningJob:
    job = db.query(ScreeningJob).filter(ScreeningJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Screening job not found")
    return job


def _detect_job_parser_mode(db: Session, job_id: str) -> str:
    fallback = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.screening_job_id == job_id,
            ProcessingLog.message.like("%Job requirement parsed with fallback mock parser%"),
        )
        .first()
    )
    if fallback:
        return "mock_fallback"
    primary = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.screening_job_id == job_id,
            ProcessingLog.message.like("%Job requirement parsed with primary LLM parser%"),
        )
        .first()
    )
    if primary:
        return "primary_llm"
    return "unknown"


def _detect_candidate_parser_mode(db: Session, job_id: str, candidate_id: str) -> str:
    fallback = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.screening_job_id == job_id,
            ProcessingLog.candidate_id == candidate_id,
            ProcessingLog.message.like("%candidate profile parsed with fallback mock parser%"),
        )
        .first()
    )
    if fallback:
        return "mock_fallback"
    primary = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.screening_job_id == job_id,
            ProcessingLog.candidate_id == candidate_id,
            ProcessingLog.message.like("%candidate profile parsed with primary LLM parser%"),
        )
        .first()
    )
    if primary:
        return "primary_llm"
    return "unknown"


def _get_job_analysis_duration_seconds(db: Session, job_id: str) -> float | None:
    start = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.screening_job_id == job_id,
            ProcessingLog.message == "Analysis started.",
        )
        .order_by(ProcessingLog.created_at.asc())
        .first()
    )
    end = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.screening_job_id == job_id,
            ProcessingLog.message.in_(["Analysis completed.", "Background analysis failed."]),
        )
        .order_by(ProcessingLog.created_at.desc())
        .first()
    )
    if not start or not end:
        return None
    delta = end.created_at - start.created_at
    return round(delta.total_seconds(), 2)


def _get_last_job_event(db: Session, job_id: str) -> str | None:
    last_log = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.screening_job_id == job_id)
        .order_by(ProcessingLog.created_at.desc())
        .first()
    )
    if not last_log:
        return None
    return f"[{last_log.level}] {last_log.message}"


def _scoring_mode_id() -> str:
    settings = get_settings()
    if settings.scoring_mode == "llm_first":
        return "gpt_5_full_ai_evaluation"
    if settings.scoring_mode == "llm_hybrid":
        return "gpt_rubric_with_deterministic_caps"
    return "deterministic_scoring"


def _scoring_engine_id() -> str:
    settings = get_settings()
    if settings.scoring_mode == "llm_first":
        return "gpt_5_full_evaluator"
    if settings.scoring_mode == "llm_hybrid":
        return "gpt_rubric_scoring"
    return "deterministic_strict"
