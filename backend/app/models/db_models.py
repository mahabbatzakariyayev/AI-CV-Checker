from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ScreeningJob(Base):
    __tablename__ = "screening_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_requirement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_requirement_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    job_requirement_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_zip_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc)

    uploaded_files: Mapped[list["UploadedFile"]] = relationship(back_populates="screening_job", cascade="all, delete-orphan")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="screening_job", cascade="all, delete-orphan")
    candidate_scores: Mapped[list["CandidateScore"]] = relationship(back_populates="screening_job", cascade="all, delete-orphan")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_job_id: Mapped[str] = mapped_column(ForeignKey("screening_jobs.id"), index=True)
    original_file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)

    screening_job: Mapped["ScreeningJob"] = relationship(back_populates="uploaded_files")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="uploaded_file")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_job_id: Mapped[str] = mapped_column(ForeignKey("screening_jobs.id"), index=True)
    uploaded_file_id: Mapped[str] = mapped_column(ForeignKey("uploaded_files.id"), index=True)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_years_experience: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_json: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_quality_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc)

    screening_job: Mapped["ScreeningJob"] = relationship(back_populates="candidates")
    uploaded_file: Mapped["UploadedFile"] = relationship(back_populates="candidates")
    score: Mapped["CandidateScore"] = relationship(back_populates="candidate", uselist=False, cascade="all, delete-orphan")


class CandidateScore(Base):
    __tablename__ = "candidate_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_job_id: Mapped[str] = mapped_column(ForeignKey("screening_jobs.id"), index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), unique=True, index=True)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_possible_score_after_caps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    recommendation_label: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)
    score_breakdown_json: Mapped[str] = mapped_column(Text, nullable=False)
    hard_requirements_json: Mapped[str] = mapped_column(Text, nullable=False)
    strengths_json: Mapped[str] = mapped_column(Text, nullable=False)
    gaps_json: Mapped[str] = mapped_column(Text, nullable=False)
    concerns_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    interview_questions_json: Mapped[str] = mapped_column(Text, nullable=False)
    strictness_notes_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)

    screening_job: Mapped["ScreeningJob"] = relationship(back_populates="candidate_scores")
    candidate: Mapped["Candidate"] = relationship(back_populates="score")


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_job_id: Mapped[str] = mapped_column(ForeignKey("screening_jobs.id"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(20), default="INFO")
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class ExportRecord(Base):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_job_id: Mapped[str] = mapped_column(ForeignKey("screening_jobs.id"), index=True)
    export_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
