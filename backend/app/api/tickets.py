"""Support ticket endpoints: CRUD, status changes, threaded messages."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.pagination import Page, PageParams, paginate
from app.db.session import get_db
from app.models.models import Client, Ticket, TicketMessage, TicketStatus, User
from app.schemas.crm import (
    TicketCreate,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    TicketStatusChange,
    TicketUpdate,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

_SORTABLE = {
    "title": Ticket.title,
    "status": Ticket.status,
    "priority": Ticket.priority,
    "created_at": Ticket.created_at,
    "id": Ticket.id,
}


@router.get("", response_model=Page[TicketOut])
def list_tickets(
    q: Optional[str] = Query(None, description="Search by title / client name"),
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    assignee_id: Optional[int] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page_params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[TicketOut]:
    stmt = select(Ticket)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.join(Client, Client.id == Ticket.client_id, isouter=True).where(
            Ticket.title.ilike(like) | Client.name.ilike(like)
        )
    if status_filter is not None:
        stmt = stmt.where(Ticket.status == status_filter)
    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)
    if client_id is not None:
        stmt = stmt.where(Ticket.client_id == client_id)
    if assignee_id is not None:
        stmt = stmt.where(Ticket.assignee_id == assignee_id)

    column = _SORTABLE.get(sort_by, Ticket.created_at)
    stmt = stmt.order_by(column.desc() if sort_dir == "desc" else column.asc())

    items, total, pages = paginate(db, stmt, page_params.page, page_params.page_size)
    return Page(
        items=[TicketOut.model_validate(t) for t in items],
        total=total,
        page=page_params.page,
        page_size=page_params.page_size,
        pages=pages,
    )


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TicketOut:
    _validate_refs(db, payload.client_id, payload.assignee_id)
    ticket = Ticket(**payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return TicketOut.model_validate(ticket)


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TicketOut:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return TicketOut.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TicketOut:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    data = payload.model_dump(exclude_unset=True)
    if any(k in data for k in ("client_id", "assignee_id")):
        _validate_refs(
            db,
            data.get("client_id", ticket.client_id),
            data.get("assignee_id", ticket.assignee_id),
        )
    if "status" in data and data["status"] is not None:
        _apply_status(ticket, data["status"])
        del data["status"]
    for field, value in data.items():
        setattr(ticket, field, value)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return TicketOut.model_validate(ticket)


@router.put("/{ticket_id}/status", response_model=TicketOut)
def change_ticket_status(
    ticket_id: int,
    payload: TicketStatusChange,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TicketOut:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _apply_status(ticket, payload.status)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return TicketOut.model_validate(ticket)


@router.post("/{ticket_id}/messages", response_model=TicketMessageOut, status_code=201)
def add_message(
    ticket_id: int,
    payload: TicketMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketMessageOut:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if ticket.status == TicketStatus.closed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reply to a closed ticket",
        )
    message = TicketMessage(ticket_id=ticket.id, author_id=current_user.id, body=payload.body)
    if ticket.status == TicketStatus.open:
        ticket.status = TicketStatus.in_progress
        db.add(ticket)
    db.add(message)
    db.commit()
    db.refresh(message)
    return TicketMessageOut.model_validate(message)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    db.delete(ticket)
    db.commit()


def _apply_status(ticket: Ticket, new_status: TicketStatus) -> None:
    ticket.status = new_status
    if new_status == TicketStatus.closed:
        ticket.closed_at = datetime.utcnow()
    else:
        ticket.closed_at = None


def _validate_refs(db: Session, client_id: Optional[int], assignee_id: Optional[int]) -> None:
    if client_id is not None and db.get(Client, client_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="client_id does not exist"
        )
    if assignee_id is not None and db.get(User, assignee_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="assignee_id does not exist"
        )

