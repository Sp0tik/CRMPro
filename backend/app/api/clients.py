"""Client endpoints: full CRUD + search, filter, sort, pagination."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.pagination import Page, PageParams, paginate
from app.db.session import get_db
from app.models.models import Activity, Client, ClientStatus, User
from app.schemas.crm import ClientCreate, ClientOut, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])

_SORTABLE = {
    "name": Client.name,
    "email": Client.email,
    "status": Client.status,
    "created_at": Client.created_at,
    "id": Client.id,
}


@router.get("", response_model=Page[ClientOut])
def list_clients(
    q: Optional[str] = Query(None, description="Search by name/email/company/phone"),
    status_filter: Optional[ClientStatus] = Query(None, alias="status"),
    manager_id: Optional[int] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page_params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[ClientOut]:
    stmt = select(Client)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Client.name.ilike(like),
                Client.email.ilike(like),
                Client.company.ilike(like),
                Client.phone.ilike(like),
            )
        )
    if status_filter is not None:
        stmt = stmt.where(Client.status == status_filter)
    if manager_id is not None:
        stmt = stmt.where(Client.manager_id == manager_id)

    column = _SORTABLE.get(sort_by, Client.created_at)
    stmt = stmt.order_by(column.desc() if sort_dir == "desc" else column.asc())

    items, total, pages = paginate(db, stmt, page_params.page, page_params.page_size)
    return Page(
        items=[ClientOut.model_validate(c) for c in items],
        total=total,
        page=page_params.page,
        page_size=page_params.page_size,
        pages=pages,
    )


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientOut:
    # Duplicate protection: same email (case-insensitive).
    email = payload.email.lower()
    dup = db.scalar(select(Client).where(func.lower(Client.email) == email))
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A client with email {email} already exists",
        )
    _validate_manager(db, payload.manager_id)
    client = Client(**{**payload.model_dump(), "email": email})
    db.add(client)
    db.flush()
    db.add(
        Activity(
            client_id=client.id,
            actor_id=current_user.id,
            type="client_created",
            message=f"Client '{client.name}' created",
        )
    )
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClientOut:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return ClientOut.model_validate(client)


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientOut:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        new_email = data["email"].lower()
        if new_email != client.email.lower():
            dup = db.scalar(select(Client).where(func.lower(Client.email) == new_email))
            if dup and dup.id != client.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A client with email {new_email} already exists",
                )
        data["email"] = new_email
    if "manager_id" in data:
        _validate_manager(db, data["manager_id"])
    for field, value in data.items():
        setattr(client, field, value)
    db.add(client)
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    # Related deals/tasks/tickets/activities cascade via ORM relationships.
    db.delete(client)
    db.commit()


def _validate_manager(db: Session, manager_id: Optional[int]) -> None:
    if manager_id is None:
        return
    if db.get(User, manager_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="manager_id does not exist"
        )
