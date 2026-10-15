"""Analytics computation from real database records.

Financial methodology (no fake numbers):
  * open_revenue      = sum(amount) of deals in qualification/proposal/negotiation
                        -> pipeline value (potential income, NOT recognised).
  * won_revenue       = sum(amount) of deals whose stage == won -> recognised revenue.
  * lost amounts are never counted as revenue.
  * weighted_pipeline = sum(amount * probability / 100) for open deals.
  * win_rate          = won / (won + lost) * 100 (0 when no closed deals).
All figures derive from rows in the database; an empty database yields zeros.
"""
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import (
    Activity,
    Client,
    Deal,
    DealStage,
    Task,
    TaskStatus,
    Ticket,
    TicketStatus,
    User,
)

OPEN_STAGES = [DealStage.qualification, DealStage.proposal, DealStage.negotiation]


def _period_bounds(date_from: Optional[date], date_to: Optional[date]):
    start = datetime.combine(date_from, datetime.min.time()) if date_from else None
    end = datetime.combine(date_to, datetime.max.time()) if date_to else None
    return start, end


def _brief_deal(d: Deal) -> dict:
    return {
        "id": d.id,
        "title": d.title,
        "amount": float(d.amount or 0),
        "stage": d.stage.value,
        "client": d.client.name if d.client else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _brief_task(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "priority": t.priority.value,
        "status": t.status.value,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "client": t.client.name if t.client else None,
        "assignee": t.assignee.full_name if t.assignee else None,
    }


def _brief_activity(a: Activity) -> dict:
    return {
        "id": a.id,
        "type": a.type,
        "message": a.message,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "client": a.client.name if a.client else None,
        "actor": a.actor.full_name if a.actor else None,
    }


def _count(db: Session, model, *where) -> int:
    stmt = select(func.count(model.id))
    for clause in where:
        stmt = stmt.where(clause)
    return db.scalar(stmt) or 0


def _sum(db: Session, column, *where) -> float:
    stmt = select(func.coalesce(func.sum(column), 0))
    for clause in where:
        stmt = stmt.where(clause)
    return float(db.scalar(stmt) or 0)


def compute_dashboard(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    manager_id: Optional[int] = None,
) -> dict:
    today = date.today()

    clients_total = _count(db, Client)
    clients_active = _count(db, Client, Client.status == "active")

    start, end = _period_bounds(date_from, date_to)
    new_clients_where = []
    if start:
        new_clients_where.append(Client.created_at >= start)
    if end:
        new_clients_where.append(Client.created_at <= end)
    clients_new_in_period = _count(db, Client, *new_clients_where)

    deals_total = _count(db, Deal)
    deals_active = _count(db, Deal, Deal.stage.in_(OPEN_STAGES))
    deals_won = _count(db, Deal, Deal.stage == DealStage.won)
    deals_lost = _count(db, Deal, Deal.stage == DealStage.lost)

    open_revenue = _sum(db, Deal.amount, Deal.stage.in_(OPEN_STAGES))
    won_revenue = _sum(db, Deal.amount, Deal.stage == DealStage.won)
    weighted_pipeline = _sum(
        db, Deal.amount * Deal.probability / 100.0, Deal.stage.in_(OPEN_STAGES)
    )
    avg_deal_size = (open_revenue + won_revenue) / deals_total if deals_total else 0.0
    closed = deals_won + deals_lost
    win_rate = (deals_won / closed * 100) if closed else 0.0

    tasks_open = _count(db, Task, Task.status != TaskStatus.done)
    tasks_done = _count(db, Task, Task.status == TaskStatus.done)
    tasks_overdue = _count(
        db, Task, Task.due_date < today, Task.status != TaskStatus.done
    )
    tickets_open = _count(db, Ticket, Ticket.status != TicketStatus.closed)

    recent_deals = [
        _brief_deal(d)
        for d in db.scalars(select(Deal).order_by(Deal.created_at.desc()).limit(5)).all()
    ]
    upcoming_tasks = [
        _brief_task(t)
        for t in db.scalars(
            select(Task)
            .where(Task.due_date >= today, Task.status != TaskStatus.done)
            .order_by(Task.due_date.asc())
            .limit(5)
        ).all()
    ]
    overdue_tasks = [
        _brief_task(t)
        for t in db.scalars(
            select(Task)
            .where(Task.due_date < today, Task.status != TaskStatus.done)
            .order_by(Task.due_date.asc())
            .limit(5)
        ).all()
    ]
    recent_activities = [
        _brief_activity(a)
        for a in db.scalars(
            select(Activity).order_by(Activity.created_at.desc()).limit(8)
        ).all()
    ]

    return {
        "clients_total": clients_total,
        "clients_active": clients_active,
        "clients_new_in_period": clients_new_in_period,
        "deals_total": deals_total,
        "deals_active": deals_active,
        "deals_won": deals_won,
        "deals_lost": deals_lost,
        "open_revenue": round(open_revenue, 2),
        "weighted_pipeline": round(weighted_pipeline, 2),
        "won_revenue": round(won_revenue, 2),
        "avg_deal_size": round(float(avg_deal_size), 2),
        "win_rate": round(win_rate, 1),
        "tasks_open": tasks_open,
        "tasks_overdue": tasks_overdue,
        "tasks_done": tasks_done,
        "tickets_open": tickets_open,
        "recent_deals": recent_deals,
        "upcoming_tasks": upcoming_tasks,
        "overdue_tasks": overdue_tasks,
        "recent_activities": recent_activities,
    }


def compute_report(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    manager_id: Optional[int] = None,
) -> dict:
    """Aggregate KPIs, per-stage breakdown and per-manager performance."""
    start, end = _period_bounds(date_from, date_to)

    deal_where = []
    if start:
        deal_where.append(Deal.created_at >= start)
    if end:
        deal_where.append(Deal.created_at <= end)
    if manager_id is not None:
        deal_where.append(Deal.manager_id == manager_id)

    deals_total = _count(db, Deal, *deal_where)
    deals_won = _count(db, Deal, *deal_where, Deal.stage == DealStage.won)
    deals_lost = _count(db, Deal, *deal_where, Deal.stage == DealStage.lost)
    won_revenue = _sum(db, Deal.amount, *deal_where, Deal.stage == DealStage.won)
    open_revenue = _sum(db, Deal.amount, *deal_where, Deal.stage.in_(OPEN_STAGES))
    closed = deals_won + deals_lost
    win_rate = (deals_won / closed * 100) if closed else 0.0

    client_where = []
    if start:
        client_where.append(Client.created_at >= start)
    if end:
        client_where.append(Client.created_at <= end)
    if manager_id is not None:
        client_where.append(Client.manager_id == manager_id)
    new_clients = _count(db, Client, *client_where)

    total_amount_all = _sum(db, Deal.amount, *deal_where)

    # Per-stage breakdown with share of total amount.
    stages = []
    for stage in DealStage:
        cnt = _count(db, Deal, *deal_where, Deal.stage == stage)
        amt = _sum(db, Deal.amount, *deal_where, Deal.stage == stage)
        share = (amt / total_amount_all * 100) if total_amount_all else 0.0
        stages.append(
            {
                "stage": stage.value,
                "count": cnt,
                "amount": round(amt, 2),
                "share": round(share, 1),
            }
        )

    # Per-manager performance.
    managers = []
    manager_rows = db.scalars(select(User).order_by(User.id)).all()
    for m in manager_rows:
        if manager_id is not None and m.id != manager_id:
            continue
        m_where = list(deal_where) + [Deal.manager_id == m.id]
        m_total = _count(db, Deal, *m_where)
        m_won = _count(db, Deal, *m_where, Deal.stage == DealStage.won)
        m_lost = _count(db, Deal, *m_where, Deal.stage == DealStage.lost)
        m_won_amt = _sum(db, Deal.amount, *m_where, Deal.stage == DealStage.won)
        m_closed = m_won + m_lost
        managers.append(
            {
                "manager_id": m.id,
                "manager_name": m.full_name,
                "deals_total": m_total,
                "deals_won": m_won,
                "deals_lost": m_lost,
                "won_amount": round(m_won_amt, 2),
                "conversion": round((m_won / m_closed * 100) if m_closed else 0.0, 1),
            }
        )

    trend = compute_trend(db, date_from, date_to, manager_id)

    kpis = [
        {"key": "new_clients", "label": "New clients", "value": new_clients,
         "display": str(new_clients), "hint": "Created in period"},
        {"key": "deals_created", "label": "Deals created", "value": deals_total,
         "display": str(deals_total), "hint": "In period"},
        {"key": "deals_won", "label": "Deals won", "value": deals_won,
         "display": str(deals_won), "hint": f"{win_rate:.1f}% win rate"},
        {"key": "deals_lost", "label": "Deals lost", "value": deals_lost,
         "display": str(deals_lost), "hint": None},
        {"key": "won_revenue", "label": "Won revenue", "value": round(won_revenue, 2),
         "display": f"{won_revenue:,.2f}", "hint": "Recognised"},
        {"key": "open_pipeline", "label": "Open pipeline", "value": round(open_revenue, 2),
         "display": f"{open_revenue:,.2f}", "hint": "Potential"},
    ]

    period = {
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }
    return {
        "period": period,
        "kpis": kpis,
        "trend": trend,
        "stages": stages,
        "managers": managers,
    }


def compute_trend(
    db: Session,
    date_from: Optional[date],
    date_to: Optional[date],
    manager_id: Optional[int],
) -> List[dict]:
    """Monthly trend series derived from created_at timestamps (portable)."""
    from collections import defaultdict

    deal_stmt = select(Deal)
    client_stmt = select(Client)
    if manager_id is not None:
        deal_stmt = deal_stmt.where(Deal.manager_id == manager_id)
        client_stmt = client_stmt.where(Client.manager_id == manager_id)
    if date_from:
        deal_stmt = deal_stmt.where(Deal.created_at >= datetime.combine(date_from, datetime.min.time()))
        client_stmt = client_stmt.where(Client.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        deal_stmt = deal_stmt.where(Deal.created_at <= datetime.combine(date_to, datetime.max.time()))
        client_stmt = client_stmt.where(Client.created_at <= datetime.combine(date_to, datetime.max.time()))

    buckets: dict = defaultdict(
        lambda: {
            "new_clients": 0,
            "deals_created": 0,
            "deals_won": 0,
            "deals_lost": 0,
            "won_amount": 0.0,
        }
    )
    for c in db.scalars(client_stmt).all():
        key = c.created_at.strftime("%Y-%m")
        buckets[key]["new_clients"] += 1
    for d in db.scalars(deal_stmt).all():
        key = d.created_at.strftime("%Y-%m")
        b = buckets[key]
        b["deals_created"] += 1
        if d.stage == DealStage.won:
            b["deals_won"] += 1
            b["won_amount"] += float(d.amount or 0)
        elif d.stage == DealStage.lost:
            b["deals_lost"] += 1

    trend = []
    for key in sorted(buckets.keys()):
        row = {"period": key}
        row.update(buckets[key])
        row["won_amount"] = round(row["won_amount"], 2)
        trend.append(row)
    return trend


