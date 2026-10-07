import json
import zipfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base
from app.models.db_models import Candidate, CandidateScore, ScreeningJob
from app.services.pipeline.screening_pipeline import ScreeningPipeline


def test_pipeline_end_to_end(tmp_path: Path):
    settings = get_settings()
    prev_backend = settings.llm_backend
    prev_provider = settings.llm_provider
    settings.upload_dir = str(tmp_path / "uploads")
    settings.export_dir = str(tmp_path / "exports")
    settings.llm_backend = "mock"
    settings.llm_provider = "mock"
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.export_dir).mkdir(parents=True, exist_ok=True)

    zip_path = tmp_path / "cvs.zip"
    cv_text = """John Doe
john@example.com
+1 555 111 2222
Experience
6 years backend engineer with Python and FastAPI.
Built RAG chatbot using Azure OpenAI and Azure AI Search.
English
"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("john_cv.txt", cv_text)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    try:
        with SessionLocal() as db:
            job = ScreeningJob(
                id="job-e2e",
                title="Senior AI Engineer",
                job_requirement_text=(
                    "Senior AI Engineer\n"
                    "Must have Python, FastAPI, Azure OpenAI, RAG.\n"
                    "Minimum 5 years experience.\n"
                    "English required."
                ),
                cv_zip_path=str(zip_path),
                status="created",
            )
            db.add(job)
            db.commit()

            pipeline = ScreeningPipeline(db)
            pipeline.analyze_screening_job(job.id)
            db.refresh(job)
            assert job.status == "completed"

            candidate = db.query(Candidate).filter(Candidate.screening_job_id == job.id).first()
            assert candidate is not None
            score = db.query(CandidateScore).filter(CandidateScore.candidate_id == candidate.id).first()
            assert score is not None
            assert score.total_score >= 0
            assert score.recommendation_label
            assert json.loads(score.score_breakdown_json)
    finally:
        settings.llm_backend = prev_backend
        settings.llm_provider = prev_provider
