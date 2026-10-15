"""Analytics endpoints: dashboard KPIs, report, and CSV export."""
import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.analytics import AnalyticsReportOut, DashboardOut
from app.services import analytics as svc

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    manager_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardOut:
    data = svc.compute_dashboard(db, date_from, date_to, manager_id)
    return DashboardOut(**data)


@router.get("/report", response_model=AnalyticsReportOut)
def report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    manager_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AnalyticsReportOut:
    data = svc.compute_report(db, date_from, date_to, manager_id)
    return AnalyticsReportOut(**data)


@router.get("/export.csv")
def export_report_csv(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    manager_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    data = svc.compute_report(db, date_from, date_to, manager_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["CRMPro Analytics Report"])
    writer.writerow(["Period from", data["period"]["date_from"] or ""])
    writer.writerow(["Period to", data["period"]["date_to"] or ""])
    writer.writerow([])

    writer.writerow(["KPI", "Value", "Hint"])
    for k in data["kpis"]:
        writer.writerow([k["label"], k["value"], k["hint"] or ""])
    writer.writerow([])

    writer.writerow(["Trend period", "New clients", "Deals created", "Won", "Lost", "Won amount"])
    for t in data["trend"]:
        writer.writerow(
            [t["period"], t["new_clients"], t["deals_created"], t["deals_won"], t["deals_lost"], t["won_amount"]]
        )
    writer.writerow([])

    writer.writerow(["Stage", "Count", "Amount", "Share %"])
    for s in data["stages"]:
        writer.writerow([s["stage"], s["count"], s["amount"], s["share"]])
    writer.writerow([])

    writer.writerow(["Manager", "Deals", "Won", "Lost", "Won amount", "Conversion %"])
    for m in data["managers"]:
        writer.writerow(
            [m["manager_name"], m["deals_total"], m["deals_won"], m["deals_lost"], m["won_amount"], m["conversion"]]
        )

    buffer.seek(0)
    filename = "crmpro_report.csv"
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
