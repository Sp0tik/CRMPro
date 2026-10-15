"""Pydantic schemas for CRM entities (clients, deals, tasks, tickets)."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.models import (
    ClientSegment,
    ClientStatus,
    DealStage,
    TaskPriority,
    TaskStatus,
    TicketPriority,
    TicketStatus,
)


# --------------------------------------------------------------------------- #
# Shared                                                                       #
# --------------------------------------------------------------------------- #
class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr


class ClientBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# --------------------------------------------------------------------------- #
# Clients                                                                      #
# --------------------------------------------------------------------------- #
class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    company: Optional[str] = Field(default=None, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=64)
    source: Optional[str] = Field(default=None, max_length=128)
    status: ClientStatus = ClientStatus.potential
    segment: Optional[ClientSegment] = None
    notes: Optional[str] = None
    manager_id: Optional[int] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    company: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=64)
    source: Optional[str] = Field(default=None, max_length=128)
    status: Optional[ClientStatus] = None
    segment: Optional[ClientSegment] = None
    notes: Optional[str] = None
    manager_id: Optional[int] = None


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    manager: Optional[UserBrief] = None


# --------------------------------------------------------------------------- #
# Deals                                                                        #
# --------------------------------------------------------------------------- #
class DealBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    client_id: int
    manager_id: Optional[int] = None
    amount: float = Field(default=0, ge=0)
    currency: str = Field(default="UAH", max_length=8)
    stage: DealStage = DealStage.qualification
    source: Optional[str] = Field(default=None, max_length=128)
    probability: int = Field(default=30, ge=0, le=100)
    loss_reason: Optional[str] = Field(default=None, max_length=255)
    deadline: Optional[date] = None


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    client_id: Optional[int] = None
    manager_id: Optional[int] = None
    amount: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, max_length=8)
    stage: Optional[DealStage] = None
    source: Optional[str] = Field(default=None, max_length=128)
    probability: Optional[int] = Field(default=None, ge=0, le=100)
    loss_reason: Optional[str] = Field(default=None, max_length=255)
    deadline: Optional[date] = None


class DealStageChange(BaseModel):
    stage: DealStage
    loss_reason: Optional[str] = Field(default=None, max_length=255)


class DealOut(DealBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientBrief] = None
    manager: Optional[UserBrief] = None


# --------------------------------------------------------------------------- #
# Tasks                                                                        #
# --------------------------------------------------------------------------- #
class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    client_id: Optional[int] = None
    deal_id: Optional[int] = None
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    client_id: Optional[int] = None
    deal_id: Optional[int] = None
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientBrief] = None
    assignee: Optional[UserBrief] = None


# --------------------------------------------------------------------------- #
# Tickets                                                                      #
# --------------------------------------------------------------------------- #
class TicketBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    client_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: TicketPriority = TicketPriority.medium


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    client_id: Optional[int] = None
    assignee_id: Optional[int] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None


class TicketStatusChange(BaseModel):
    status: TicketStatus


class TicketMessageCreate(BaseModel):
    body: str = Field(min_length=1)


class TicketMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    body: str
    created_at: datetime
    author: Optional[UserBrief] = None


class TicketOut(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    client: Optional[ClientBrief] = None
    assignee: Optional[UserBrief] = None
    messages: List[TicketMessageOut] = []


# --------------------------------------------------------------------------- #
# Activity                                                                     #
# --------------------------------------------------------------------------- #
class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    type: str
    message: str
    created_at: datetime
    actor: Optional[UserBrief] = None

