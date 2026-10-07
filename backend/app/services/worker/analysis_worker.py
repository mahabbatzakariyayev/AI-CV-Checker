from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from app.config import get_settings
from app.database import SessionLocal
from app.models.db_models import ScreeningJob
from app.services.pipeline.screening_pipeline import ScreeningPipeline
from app.utils.logging import log_event, log_exception_event


class AnalysisWorker:
    def __init__(self) -> None:
        settings = get_settings()
        self._executor = ThreadPoolExecutor(max_workers=settings.analysis_worker_max_workers)
        self._active_jobs: set[str] = set()
        self._lock = Lock()

    def enqueue(self, job_id: str) -> dict:
        with self._lock:
            if job_id in self._active_jobs:
                return {"job_id": job_id, "status": "already_queued_or_processing"}
            self._active_jobs.add(job_id)
        with SessionLocal() as db:
            job = db.query(ScreeningJob).filter(ScreeningJob.id == job_id).first()
            if not job:
                with self._lock:
                    self._active_jobs.discard(job_id)
                raise ValueError("Screening job not found")
            if job.status in {"processing", "queued"}:
                with self._lock:
                    self._active_jobs.discard(job_id)
                return {"job_id": job_id, "status": job.status}
            job.status = "queued"
            db.commit()
            log_event(db, job_id, "Job queued for background analysis.")

        future = self._executor.submit(self._run, job_id)
        future.add_done_callback(lambda result: self._on_done(job_id, result))
        return {"job_id": job_id, "status": "queued"}

    def is_active(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._active_jobs

    def _run(self, job_id: str) -> None:
        with SessionLocal() as db:
            pipeline = ScreeningPipeline(db)
            pipeline.analyze_screening_job(job_id)

    def _on_done(self, job_id: str, future: Future) -> None:
        with self._lock:
            self._active_jobs.discard(job_id)
        exc = future.exception()
        if exc:
            with SessionLocal() as db:
                job = db.query(ScreeningJob).filter(ScreeningJob.id == job_id).first()
                if job:
                    job.status = "failed"
                    db.commit()
                log_exception_event(db, job_id, "Background analysis failed.", exc)


analysis_worker = AnalysisWorker()
