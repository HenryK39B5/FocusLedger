from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.schemas.qclaw import QClawDailyReportRead
from src.services.qclaw import QClawReportService

router = APIRouter(prefix="/integrations/qclaw", tags=["qclaw"])
service = QClawReportService()


@router.get("/daily-report", response_model=QClawDailyReportRead)
def get_qclaw_daily_report(
    date: str | None = None,
    source_id: str | None = None,
    source_group: str | None = None,
    limit: int = 12,
    style: str = "brief",
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    settings = get_settings()
    if settings.qclaw_integration_key and x_integration_key != settings.qclaw_integration_key:
        raise HTTPException(status_code=401, detail="invalid integration key")

    safe_limit = min(max(limit, 1), 30)
    return service.build_daily_report_reply(
        db,
        report_date=date,
        source_id=source_id,
        source_group=source_group,
        limit=safe_limit,
        style=style if style in {"brief", "full"} else "brief",
    )
