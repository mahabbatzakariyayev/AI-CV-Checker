from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import ScreeningJob
from app.services.export.excel_export_service import ExcelExportService
from app.services.export.json_export_service import JsonExportService

router = APIRouter(prefix="/api/screening-jobs", tags=["exports"])


@router.get("/{job_id}/export/excel")
def export_excel(job_id: str, db: Session = Depends(get_db)) -> FileResponse:
    job = db.query(ScreeningJob).filter(ScreeningJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Screening job not found")
    path = ExcelExportService().export(db, job)
    return FileResponse(path=path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=path.name)


@router.get("/{job_id}/export/json")
def export_json(job_id: str, db: Session = Depends(get_db)) -> FileResponse:
    job = db.query(ScreeningJob).filter(ScreeningJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Screening job not found")
    path = JsonExportService().export(db, job)
    return FileResponse(path=path, media_type="application/json", filename=path.name)
