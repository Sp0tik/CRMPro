"""Deal endpoints: CRUD + stage transitions + history + filters."""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.pagination import Page, PageParams, paginate
from app.db.session import get_db
from app.models.models import Activity, Client, Deal, DealStage, User
from app.schemas.crm import DealCreate, DealOut, DealStageChange, DealUpdate

router = APIRouter(prefix="/deals", tags=["deals"])

_SORTABLE = {
    "title": Deal.title,
    "amount": Deal.amount,
    "stage": Deal.stage,
    "deadline": Deal.deadline,
    "created_at": Deal.created_at,
    "id": Deal.id,
}


@router.get("", response_model=Page[DealOut])
def list_deals(
    q: Optional[str] = Query(None, description="Search by title / client name"),
    stage: Optional[DealStage] = Query(None),
    manager_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page_params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[DealOut]:
    stmt = select(Deal)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.join(Client, Client.id == Deal.client_id).where(
            or_(Deal.title.ilike(like), Client.name.ilike(like))
        )
    if stage is not None:
        stmt = stmt.where(Deal.stage == stage)
    if manager_id is not None:
        stmt = stmt.where(Deal.manager_id == manager_id)
    if client_id is not None:
        stmt = stmt.where(Deal.client_id == client_id)
    if date_from is not None:
        stmt = stmt.where(Deal.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        stmt = stmt.where(Deal.created_at <= datetime.combine(date_to, datetime.max.time()))

    column = _SORTABLE.get(sort_by, Deal.created_at)
    stmt = stmt.order_by(column.desc() if sort_dir == "desc" else column.asc())

    items, total, pages = paginate(db, stmt, page_params.page, page_params.page_size)
    return Page(
        items=[DealOut.model_validate(d) for d in items],
        total=total,
        page=page_params.page,
        page_size=page_params.page_size,
        pages=pages,
    )


@router.post("", response_model=DealOut, status_code=status.HTTP_201_CREATED)
def create_deal(
    payload: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealOut:
    _validate_refs(db, payload.client_id, payload.manager_id)
    data = payload.model_dump()
    # Default the responsible manager to the creating user when unspecified.
    if data.get("manager_id") is None:
        data["manager_id"] = current_user.id
    deal = Deal(**data)
    db.add(deal)
    db.flush()
    db.add(
        Activity(
            client_id=deal.client_id,
            actor_id=current_user.id,
            type="deal_created",
            message=f"Deal '{deal.title}' created ({deal.stage.value})",
        )
    )
    db.commit()
    db.refresh(deal)
    return DealOut.model_validate(deal)


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DealOut:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return DealOut.model_validate(deal)


@router.patch("/{deal_id}", response_model=DealOut)
def update_deal(
    deal_id: int,
    payload: DealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealOut:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    data = payload.model_dump(exclude_unset=True)
    if "client_id" in data and data["client_id"] is not None:
        _validate_refs(db, data["client_id"], data.get("manager_id"))
    if "manager_id" in data:
        _validate_refs(db, deal.client_id, data["manager_id"])
    old_stage = deal.stage
    for field, value in data.items():
        setattr(deal, field, value)
    if "stage" in data and data["stage"] is not None and data["stage"] != old_stage:
        _log_stage_change(deal, data["stage"], current_user, db, old_stage)
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return DealOut.model_validate(deal)


@router.put("/{deal_id}/stage", response_model=DealOut)
def change_deal_stage(
    deal_id: int,
    payload: DealStageChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealOut:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    old_stage = deal.stage
    deal.stage = payload.stage
    if payload.stage == DealStage.lost:
        deal.probability = 0
        deal.loss_reason = payload.loss_reason or deal.loss_reason
    elif payload.stage == DealStage.won:
        deal.probability = 100
        deal.loss_reason = None
    _log_stage_change(deal, payload.stage, current_user, db, old_stage)
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return DealOut.model_validate(deal)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    db.delete(deal)
    db.commit()


def _log_stage_change(
    deal: Deal,
    new_stage: DealStage,
    actor: User,
    db: Session,
    old_stage: Optional[DealStage],
) -> None:
    """Record an activity entry when a deal changes stage."""
    verb = {DealStage.won: "won", DealStage.lost: "lost"}.get(new_stage, "moved")
    db.add(
        Activity(
            client_id=deal.client_id,
            actor_id=actor.id,
            type=f"deal_{verb}",
            message=f"Deal '{deal.title}' {verb}: {old_stage.value} -> {new_stage.value}",
        )
    )


def _validate_refs(db: Session, client_id: Optional[int], manager_id: Optional[int]) -> None:
    if client_id is not None and db.get(Client, client_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="client_id does not exist"
        )
    if manager_id is not None and db.get(User, manager_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="manager_id does not exist"
        )

