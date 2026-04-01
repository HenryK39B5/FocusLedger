from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.schemas.dashboard import IngestionJobCreate, IngestionJobListRead, IngestionJobRead
from src.services.ingestion_jobs import ingestion_job_service

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion-jobs"])


@router.post("", response_model=IngestionJobRead)
def create_ingestion_job(
    payload: IngestionJobCreate,
    db: Session = Depends(db_session),
):
    try:
        job = ingestion_job_service.create_job(db, get_settings(), payload)
        db.commit()
        db.refresh(job)
        ingestion_job_service.start_job(get_settings(), job.id)
        return ingestion_job_service.get_job_read(db, job.id)
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if message == "source not found":
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=409, detail=message) from exc


@router.get("", response_model=IngestionJobListRead)
def list_ingestion_jobs(
    source_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(db_session),
):
    return ingestion_job_service.list_jobs(db, source_id=source_id, limit=limit)


@router.get("/{job_id}", response_model=IngestionJobRead)
def get_ingestion_job(
    job_id: str,
    db: Session = Depends(db_session),
):
    job = ingestion_job_service.get_job_read(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
