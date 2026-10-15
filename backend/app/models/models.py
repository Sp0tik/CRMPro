"""SQLAlchemy ORM models for CRMPro.

Naming conventions align with Alembic autogenerate so migrations produce
stable, deterministic names. Monetary values are stored as NUMERIC(14, 2).
Enums are stored as portable strings (native_enum=False) so the same schema
works on both SQLite (local dev/test) and PostgreSQL (production).
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    MetaData,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Stable naming convention for Alembic autogenerate.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
Base.metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UserRole(str, PyEnum):
    admin = "admin"
    manager = "manager"


class ClientStatus(str, PyEnum):
    active = "active"
    potential = "potential"
    vip = "vip"
    inactive = "inactive"


class ClientSegment(str, PyEnum):
    enterprise = "enterprise"
    smb = "smb"
    startup = "startup"


class DealStage(str, PyEnum):
    qualification = "qualification"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class TaskStatus(str, PyEnum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, PyEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketStatus(str, PyEnum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class TicketPriority(str, PyEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


def _enum(py_enum) -> Enum:
    """Create a portable string Enum column type."""
    return Enum(
        py_enum, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e]
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.manager, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    managed_clients: Mapped[List["Client"]] = relationship(
        back_populates="manager", foreign_keys="Client.manager_id"
    )
    assigned_deals: Mapped[List["Deal"]] = relationship(
        back_populates="manager", foreign_keys="Deal.manager_id"
    )
    assigned_tasks: Mapped[List["Task"]] = relationship(
        back_populates="assignee", foreign_keys="Task.assignee_id"
    )
    assigned_tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="assignee", foreign_keys="Ticket.assignee_id"
    )


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_status", "status"),
        Index("ix_clients_manager_id", "manager_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[ClientStatus] = mapped_column(
        _enum(ClientStatus), default=ClientStatus.potential, nullable=False
    )
    segment: Mapped[Optional[ClientSegment]] = mapped_column(_enum(ClientSegment), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    manager: Mapped[Optional["User"]] = relationship(
        back_populates="managed_clients", foreign_keys=[manager_id]
    )
    deals: Mapped[List["Deal"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    activities: Mapped[List["Activity"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        Index("ix_deals_stage", "stage"),
        Index("ix_deals_client_id", "client_id"),
        Index("ix_deals_manager_id", "manager_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    manager_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UAH")
    stage: Mapped[DealStage] = mapped_column(
        _enum(DealStage), default=DealStage.qualification, nullable=False
    )
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    probability: Mapped[int] = mapped_column(default=30, nullable=False)
    loss_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="deals")
    manager: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_deals", foreign_keys=[manager_id]
    )
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_client_id", "client_id"),
        Index("ix_tasks_deal_id", "deal_id"),
        Index("ix_tasks_assignee_id", "assignee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        _enum(TaskStatus), default=TaskStatus.todo, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        _enum(TaskPriority), default=TaskPriority.medium, nullable=False
    )
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True
    )
    deal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"), nullable=True
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    client: Mapped[Optional["Client"]] = relationship(back_populates="tasks")
    deal: Mapped[Optional["Deal"]] = relationship(back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_tasks", foreign_keys=[assignee_id]
    )


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_client_id", "client_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[TicketStatus] = mapped_column(
        _enum(TicketStatus), default=TicketStatus.open, nullable=False
    )
    priority: Mapped[TicketPriority] = mapped_column(
        _enum(TicketPriority), default=TicketPriority.medium, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    client: Mapped[Optional["Client"]] = relationship(back_populates="tickets")
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_tickets", foreign_keys=[assignee_id]
    )
    messages: Mapped[List["TicketMessage"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    __table_args__ = (Index("ix_ticket_messages_ticket_id", "ticket_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="messages")
    author: Mapped[Optional["User"]] = relationship(foreign_keys=[author_id])


class Activity(Base):
    """Activity / audit log entry attached to a client."""

    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_client_id", "client_id"),
        Index("ix_activities_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)  # created, deal_won, note ...
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="activities")
    actor: Mapped[Optional["User"]] = relationship(foreign_keys=[actor_id])



