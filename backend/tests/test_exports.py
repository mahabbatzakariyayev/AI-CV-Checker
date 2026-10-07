import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.db_models import Candidate, CandidateScore, ScreeningJob, UploadedFile
from app.services.export.excel_export_service import ExcelExportService
from app.services.export.json_export_service import JsonExportService


def test_export_generation(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        job = ScreeningJob(id="j1", title="Job", status="completed")
        db.add(job)
        file = UploadedFile(id="f1", screening_job_id="j1", original_file_name="cv.txt", stored_file_path="/tmp/cv.txt", file_type="txt", file_size=12, status="processed")
        db.add(file)
        candidate = Candidate(
            id="c1",
            screening_job_id="j1",
            uploaded_file_id="f1",
            candidate_name="Candidate",
            email="c@example.com",
            phone="123",
            location="Baku",
            total_years_experience=5,
            candidate_json=json.dumps({"candidate_name": "Candidate"}),
            extraction_quality_json=json.dumps({"quality_level": "high", "score": 90}),
            status="processed",
        )
        db.add(candidate)
        score = CandidateScore(
            screening_job_id="j1",
            candidate_id="c1",
            total_score=800,
            max_possible_score_after_caps=900,
            recommendation_label="Needs Recruiter Review",
            confidence_level="Medium",
            score_breakdown_json=json.dumps({"eligibility_and_must_have_fit": 200}),
            hard_requirements_json=json.dumps([]),
            strengths_json=json.dumps(["Python"]),
            gaps_json=json.dumps(["Kubernetes"]),
            concerns_json=json.dumps([]),
            evidence_json=json.dumps([]),
            interview_questions_json=json.dumps(["Q1"]),
            strictness_notes_json=json.dumps([]),
        )
        db.add(score)
        db.commit()

        excel_service = ExcelExportService()
        json_service = JsonExportService()
        excel_service.settings.export_dir = str(tmp_path)
        json_service.settings.export_dir = str(tmp_path)
        excel_path = excel_service.export(db, job)
        json_path = json_service.export(db, job)

        assert excel_path.exists()
        assert json_path.exists()
