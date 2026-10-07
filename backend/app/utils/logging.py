import json
import logging
import traceback
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db_models import ProcessingLog


def configure_app_logging() -> None:
    settings = get_settings()
    log_file = Path(settings.app_log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        return
    log_level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root.setLevel(log_level)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def exception_details(exc: Exception) -> dict[str, Any]:
    return {
        "error_type": exc.__class__.__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(limit=25),
    }


def log_event(
    db: Session,
    screening_job_id: str,
    message: str,
    level: str = "INFO",
    details: dict[str, Any] | None = None,
    candidate_id: str | None = None,
) -> None:
    payload = details or {}
    logger = get_logger("cv_checker.processing")
    log_line = f"job={screening_job_id} candidate={candidate_id or '-'} {message}"
    getattr(logger, level.lower(), logger.info)(f"{log_line} | details={payload}")
    record = ProcessingLog(
        screening_job_id=screening_job_id,
        candidate_id=candidate_id,
        level=level,
        message=message,
        details_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(record)
    db.commit()


def log_exception_event(
    db: Session,
    screening_job_id: str,
    message: str,
    exc: Exception,
    candidate_id: str | None = None,
) -> None:
    log_event(
        db=db,
        screening_job_id=screening_job_id,
        message=message,
        level="ERROR",
        details=exception_details(exc),
        candidate_id=candidate_id,
    )
