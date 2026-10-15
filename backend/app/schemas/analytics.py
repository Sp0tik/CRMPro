"""Pydantic schemas for dashboard / analytics payloads."""
from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel


class PeriodFilter(BaseModel):
    """Query parameters shared by analytics endpoints."""

    date_from: Optional[date] = None
    date_to: Optional[date] = None
    manager_id: Optional[int] = None


class KpiCard(BaseModel):
    key: str
    label: str
    value: float
    display: str
    hint: Optional[str] = None


class TrendPoint(BaseModel):
    period: str  # e.g. "2024-07" or "2024-07-22"
    new_clients: int = 0
    deals_created: int = 0
    deals_won: int = 0
    deals_lost: int = 0
    won_amount: float = 0.0


class StageCount(BaseModel):
    stage: str
    count: int
    amount: float
    share: float


class ManagerPerformance(BaseModel):
    manager_id: Optional[int]
    manager_name: str
    deals_total: int
    deals_won: int
    deals_lost: int
    won_amount: float
    conversion: float


class DashboardOut(BaseModel):
    clients_total: int
    clients_active: int
    clients_new_in_period: int
    deals_total: int
    deals_active: int
    deals_won: int
    deals_lost: int
    open_revenue: float  # sum of amount for active deals (pipeline)
    weighted_pipeline: float  # sum(amount * probability/100) for active deals
    won_revenue: float  # sum of amount for won deals (recognised)
    avg_deal_size: float
    win_rate: float  # won / (won + lost) * 100
    tasks_open: int
    tasks_overdue: int
    tasks_done: int
    tickets_open: int
    recent_deals: List[dict]
    upcoming_tasks: List[dict]
    overdue_tasks: List[dict]
    recent_activities: List[dict]


class AnalyticsReportOut(BaseModel):
    period: Dict[str, Optional[str]]
    kpis: List[KpiCard]
    trend: List[TrendPoint]
    stages: List[StageCount]
    managers: List[ManagerPerformance]
