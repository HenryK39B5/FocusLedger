from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.schemas.dashboard import IngestionResult
from src.services.ingestion import IngestionService
from src.services.sources import SourceService

router = APIRouter(prefix="/ingestions", tags=["ingestions"])
service = IngestionService()


@router.post("/{source_id}/run", response_model=IngestionResult)
def run_ingestion(
    source_id: str,
    page_start: int = 1,
    page_end: int = 20,
    since_days: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(db_session),
):
    source = SourceService().get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    result = service.run_source(
        db,
        get_settings(),
        source,
        page_start=page_start,
        page_end=page_end,
        since_days=since_days,
        date_from=date_from,
        date_to=date_to,
    )
    db.commit()
    return result
