import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db_models import Candidate, CandidateScore, ExportRecord, ScreeningJob, UploadedFile


class ExcelExportService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def export(self, db: Session, job: ScreeningJob) -> Path:
        rows = (
            db.query(Candidate, CandidateScore, UploadedFile)
            .join(CandidateScore, CandidateScore.candidate_id == Candidate.id)
            .join(UploadedFile, UploadedFile.id == Candidate.uploaded_file_id)
            .filter(Candidate.screening_job_id == job.id)
            .order_by(CandidateScore.total_score.desc())
            .all()
        )
        output = Path(self.settings.export_dir) / f"{job.id}_results.xlsx"
        output.parent.mkdir(parents=True, exist_ok=True)

        summary_data = {
            "metric": ["screening_job_title", "total_cvs", "processed_cvs", "failed_cvs", "average_score", "top_candidate", "generated_at"],
            "value": [
                job.title,
                len(rows),
                len(rows),
                db.query(UploadedFile).filter(UploadedFile.screening_job_id == job.id, UploadedFile.status == "failed").count(),
                round(sum(item[1].total_score for item in rows) / max(1, len(rows)), 2),
                rows[0][0].candidate_name if rows else "",
                datetime.now(timezone.utc).isoformat(),
            ],
        }
        ranked = []
        detailed = []
        evidence_rows = []
        questions_rows = []
        for rank, (candidate, score, uploaded) in enumerate(rows, start=1):
            strengths = json.loads(score.strengths_json)
            gaps = json.loads(score.gaps_json)
            hard = json.loads(score.hard_requirements_json)
            extraction = json.loads(candidate.extraction_quality_json)
            breakdown = json.loads(score.score_breakdown_json)
            ranked.append(
                {
                    "rank": rank,
                    "candidate_name": candidate.candidate_name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "score": score.total_score,
                    "recommendation": score.recommendation_label,
                    "confidence": score.confidence_level,
                    "years_experience": candidate.total_years_experience,
                    "strengths": "; ".join(strengths[:3]),
                    "gaps": "; ".join(gaps[:3]),
                    "missing_critical_requirements": "; ".join(
                        [h["requirement"] for h in hard if h["status"] == "missing"]
                    ),
                    "extraction_quality": extraction.get("quality_level", ""),
                    "original_file": uploaded.original_file_name,
                }
            )
            detailed.append(
                {
                    "candidate": candidate.candidate_name,
                    "total_score": score.total_score,
                    "eligibility_score": breakdown.get("eligibility_and_must_have_fit", 0),
                    "technical_depth_score": breakdown.get("technical_depth", 0),
                    "experience_score": breakdown.get("relevant_professional_experience", 0),
                    "project_score": breakdown.get("project_and_achievement_evidence", 0),
                    "seniority_score": breakdown.get("seniority_and_ownership", 0),
                    "education_score": breakdown.get("education_and_certifications", 0),
                    "communication_score": breakdown.get("communication_and_language", 0),
                    "evidence_score": breakdown.get("evidence_confidence", 0),
                    "max_possible_score_after_caps": score.max_possible_score_after_caps,
                }
            )
            for ev in json.loads(score.evidence_json):
                evidence_rows.append(
                    {
                        "candidate": candidate.candidate_name,
                        "claim": ev.get("claim", ""),
                        "evidence_text": ev.get("source_text", ""),
                        "page": ev.get("page_number", ""),
                        "section": ev.get("section", ""),
                        "confidence": ev.get("confidence", ""),
                    }
                )
            for question in json.loads(score.interview_questions_json):
                questions_rows.append({"candidate": candidate.candidate_name, "question": question})

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
            pd.DataFrame(ranked).to_excel(writer, sheet_name="Ranked Candidates", index=False)
            pd.DataFrame(detailed).to_excel(writer, sheet_name="Detailed Scores", index=False)
            pd.DataFrame(evidence_rows).to_excel(writer, sheet_name="Evidence", index=False)
            pd.DataFrame(questions_rows).to_excel(writer, sheet_name="Interview Questions", index=False)

        db.add(ExportRecord(screening_job_id=job.id, export_type="excel", file_path=str(output)))
        db.commit()
        return output
