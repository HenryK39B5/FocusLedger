from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.schemas.reports import DailyReportRead
from src.services.reports import DailyReportService

router = APIRouter(prefix="/reports", tags=["reports"])
service = DailyReportService()


@router.get("/daily", response_model=DailyReportRead)
def get_daily_report(
    date: str | None = None,
    source_id: str | None = None,
    source_group: str | None = None,
    limit: int = 20,
    db: Session = Depends(db_session),
):
    return service.build_daily_report(db, report_date=date, source_id=source_id, source_group=source_group, limit=limit)
