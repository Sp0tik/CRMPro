"""Reusable pagination envelope + query params."""
from typing import Generic, List, Tuple, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Query(1, ge=1, description="1-based page number")
    page_size: int = Query(20, ge=1, le=200, description="Items per page")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


def count_query(db: Session, stmt: Select) -> int:
    """Row count for a Select without loading rows (COUNT over a subquery)."""
    subq = stmt.order_by(None).subquery()
    return int(db.scalar(select(func.count()).select_from(subq)) or 0)


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> Tuple[list, int, int]:
    """Return (items, total, pages) for a SQLAlchemy 2.x Select statement."""
    total = count_query(db, stmt)
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    pages = (total + page_size - 1) // page_size if page_size else 0
    return list(items), total, pages

