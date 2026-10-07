import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db_models import Candidate, CandidateScore, ExportRecord, ScreeningJob


class JsonExportService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def export(self, db: Session, job: ScreeningJob) -> Path:
        candidates = (
            db.query(Candidate, CandidateScore)
            .join(CandidateScore, CandidateScore.candidate_id == Candidate.id)
            .filter(Candidate.screening_job_id == job.id)
            .order_by(CandidateScore.total_score.desc())
            .all()
        )

        payload = {
            "job": {
                "id": job.id,
                "title": job.title,
                "status": job.status,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "candidates": [],
        }
        for candidate, score in candidates:
            payload["candidates"].append(
                {
                    "candidate": json.loads(candidate.candidate_json),
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
            )
        output = Path(self.settings.export_dir) / f"{job.id}_results.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        db.add(ExportRecord(screening_job_id=job.id, export_type="json", file_path=str(output)))
        db.commit()
        return output
