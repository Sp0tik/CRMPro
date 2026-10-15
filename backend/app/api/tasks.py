"""Task endpoints: CRUD + filters (today/upcoming/overdue/done)."""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.pagination import Page, PageParams, paginate
from app.db.session import get_db
from app.models.models import Client, Deal, Task, TaskStatus, User
from app.schemas.crm import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

_SORTABLE = {
    "title": Task.title,
    "priority": Task.priority,
    "status": Task.status,
    "due_date": Task.due_date,
    "created_at": Task.created_at,
    "id": Task.id,
}


@router.get("", response_model=Page[TaskOut])
def list_tasks(
    filter: Optional[str] = Query(
        None, pattern="^(today|upcoming|overdue|done|open)$"
    ),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    deal_id: Optional[int] = Query(None),
    assignee_id: Optional[int] = Query(None),
    sort_by: str = Query("due_date"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page_params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[TaskOut]:
    stmt = select(Task)
    today = date.today()

    if filter == "today":
        stmt = stmt.where(Task.due_date == today, Task.status != TaskStatus.done)
    elif filter == "upcoming":
        stmt = stmt.where(Task.due_date > today, Task.status != TaskStatus.done)
    elif filter == "overdue":
        stmt = stmt.where(Task.due_date < today, Task.status != TaskStatus.done)
    elif filter == "done":
        stmt = stmt.where(Task.status == TaskStatus.done)
    elif filter == "open":
        stmt = stmt.where(Task.status != TaskStatus.done)

    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if client_id is not None:
        stmt = stmt.where(Task.client_id == client_id)
    if deal_id is not None:
        stmt = stmt.where(Task.deal_id == deal_id)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)

    column = _SORTABLE.get(sort_by, Task.due_date)
    # NULLs last regardless of direction for a predictable ordering.
    stmt = stmt.order_by(column.is_(None), column.desc() if sort_dir == "desc" else column.asc())

    items, total, pages = paginate(db, stmt, page_params.page, page_params.page_size)
    return Page(
        items=[TaskOut.model_validate(t) for t in items],
        total=total,
        page=page_params.page,
        page_size=page_params.page_size,
        pages=pages,
    )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TaskOut:
    _validate_refs(db, payload.client_id, payload.deal_id, payload.assignee_id)
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TaskOut:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskOut.model_validate(task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TaskOut:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    data = payload.model_dump(exclude_unset=True)
    if any(k in data for k in ("client_id", "deal_id", "assignee_id")):
        _validate_refs(
            db,
            data.get("client_id", task.client_id),
            data.get("deal_id", task.deal_id),
            data.get("assignee_id", task.assignee_id),
        )
    for field, value in data.items():
        setattr(task, field, value)
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()


def _validate_refs(
    db: Session,
    client_id: Optional[int],
    deal_id: Optional[int],
    assignee_id: Optional[int],
) -> None:
    if client_id is not None and db.get(Client, client_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="client_id does not exist"
        )
    if deal_id is not None and db.get(Deal, deal_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="deal_id does not exist"
        )
    if assignee_id is not None and db.get(User, assignee_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="assignee_id does not exist"
        )
