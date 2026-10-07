from datetime import datetime

from pydantic import BaseModel, Field


class CreateScreeningJobRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)


class ScreeningJobResponse(BaseModel):
    id: str
    title: str
    status: str


class JobRequirementTextRequest(BaseModel):
    text: str = Field(min_length=10)


class ScreeningStatusResponse(BaseModel):
    job_id: str
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    created_at: datetime
    updated_at: datetime
    errors: list[str] = Field(default_factory=list)

