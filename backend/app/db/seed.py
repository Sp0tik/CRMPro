"""Idempotent demo-data seeder.

Safe to run repeatedly:
  * Users are matched by email; existing users keep their password.
  * Clients are matched by email; existing clients are updated, not duplicated.
  * Deals/tasks/tickets are only added when the target tables are empty, so
    running the seeder twice will not double the pipeline.

No real personal data is used — every record is clearly fictional.
"""
import argparse
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.models import (
    Activity,
    Client,
    ClientSegment,
    ClientStatus,
    Deal,
    DealStage,
    Task,
    TaskPriority,
    TaskStatus,
    Ticket,
    TicketMessage,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)

DEMO_PASSWORD = "Admin123!"  # local demo only; documented in README.

USERS = [
    ("admin@crmpro.example", "Alex Admin", UserRole.admin),
    ("olena@crmpro.example", "Olena Koval", UserRole.manager),
    ("denis@crmpro.example", "Denis Shevchenko", UserRole.manager),
    ("maryna@crmpro.example", "Maryna Lysenko", UserRole.manager),
]

# name, company, email, phone, source, status, segment, manager_email, notes
CLIENTS = [
    ("Alpha Group", "Alpha Group LLC", "contact@alpha.example", "+380 44 000 11 22",
     "referral", ClientStatus.active, ClientSegment.enterprise, "olena@crmpro.example",
     "Key enterprise account."),
    ("Ihor Melnyk", "Private entrepreneur", "ihor.melnyk@example.com", "+380 67 000 22 33",
     "website", ClientStatus.active, ClientSegment.smb, "denis@crmpro.example", None),
    ("BudMaster", "BudMaster LLC", "sales@budmaster.example", "+380 50 000 33 44",
     "cold_call", ClientStatus.potential, ClientSegment.smb, "olena@crmpro.example", None),
    ("UkrTech", "UkrTech PJSC", "info@ukrtech.example", "+380 63 000 44 55",
     "partner", ClientStatus.vip, ClientSegment.enterprise, "maryna@crmpro.example",
     "Long-term partner."),
    ("Nova Wave", "Nova Wave LLC", "hello@novawave.example", "+380 73 000 55 66",
     "website", ClientStatus.inactive, ClientSegment.startup, "denis@crmpro.example", None),
]


def _get_or_create_user(db: Session, email: str, name: str, role: UserRole) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            full_name=name,
            hashed_password=hash_password(DEMO_PASSWORD),
            role=role,
        )
        db.add(user)
        db.flush()
    return user


def _get_or_create_client(db: Session, data: tuple, manager: User) -> Client:
    name, company, email, phone, source, status, segment, _mgr, notes = data
    client = db.scalar(select(Client).where(func.lower(Client.email) == email.lower()))
    if client is None:
        client = Client(
            name=name, company=company, email=email.lower(), phone=phone, source=source,
            status=status, segment=segment, notes=notes, manager_id=manager.id,
        )
        db.add(client)
        db.flush()
        db.add(
            Activity(
                client_id=client.id, actor_id=manager.id, type="client_created",
                message=f"Client '{client.name}' created (seed)",
            )
        )
    return client


# title, client_email, amount, stage, probability, manager_email, deadline_offset_days, source
DEALS = [
    ("CRM implementation", "contact@alpha.example", 85000, DealStage.negotiation, 70,
     "olena@crmpro.example", 30, "referral"),
    ("Annual support contract", "info@ukrtech.example", 120000, DealStage.won, 100,
     "maryna@crmpro.example", -10, "partner"),
    ("Custom module development", "sales@budmaster.example", 45000, DealStage.qualification, 30,
     "olena@crmpro.example", 45, "cold_call"),
    ("Software licences", "ihor.melnyk@example.com", 18000, DealStage.proposal, 50,
     "denis@crmpro.example", 20, "website"),
    ("Q3 consulting", "info@ukrtech.example", 32000, DealStage.lost, 0,
     "maryna@crmpro.example", -25, "partner"),
    ("Cloud migration pilot", "hello@novawave.example", 26000, DealStage.qualification, 20,
     "denis@crmpro.example", 60, "website"),
]

# title, description, priority, status, client_email, assignee_email, due_offset_days
TASKS = [
    ("Call Alpha Group about proposal", "Discuss the revised pricing.",
     TaskPriority.high, TaskStatus.todo, "contact@alpha.example", "olena@crmpro.example", 2),
    ("Prepare quote for BudMaster", "Draft the commercial offer document.",
     TaskPriority.medium, TaskStatus.todo, "sales@budmaster.example", "olena@crmpro.example", 5),
    ("Send invoice to UkrTech", "Invoice for the support contract.",
     TaskPriority.high, TaskStatus.done, "info@ukrtech.example", "maryna@crmpro.example", -3),
    ("Update Melnyk contact details", "Confirm new phone number.",
     TaskPriority.low, TaskStatus.todo, "ihor.melnyk@example.com", "denis@crmpro.example", 8),
    ("Follow up Nova Wave", "Check interest in cloud pilot.",
     TaskPriority.medium, TaskStatus.in_progress, "hello@novawave.example", "denis@crmpro.example", 1),
    ("Overdue: renew partner agreement", "Agreement lapsed last week.",
     TaskPriority.critical, TaskStatus.todo, "info@ukrtech.example", "maryna@crmpro.example", -5),
]

# title, description, priority, status, client_email, assignee_email, first_message
TICKETS = [
    ("Login error reported", "Customer cannot sign in after password reset.",
     TicketPriority.critical, TicketStatus.open, "info@ukrtech.example", "maryna@crmpro.example",
     "Thanks for reaching out - we are investigating the login issue."),
    ("Feature request: CSV import", "Would like bulk import of contacts.",
     TicketPriority.low, TicketStatus.in_progress, "contact@alpha.example", "olena@crmpro.example",
     "Noted - we have added this to the roadmap."),
    ("Billing question", "Clarification on the last invoice.",
     TicketPriority.medium, TicketStatus.closed, "ihor.melnyk@example.com", "denis@crmpro.example",
     "Resolved - invoice details sent by email."),
]


def seed(force: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        users_by_email = {
            email: _get_or_create_user(db, email, name, role)
            for email, name, role in USERS
        }
        db.flush()

        clients_by_email = {}
        for cdata in CLIENTS:
            mgr = users_by_email.get(cdata[7]) or users_by_email["admin@crmpro.example"]
            client = _get_or_create_client(db, cdata, mgr)
            clients_by_email[cdata[2].lower()] = client
        db.flush()

        today = date.today()

        deals_exist = db.scalar(select(func.count(Deal.id))) or 0
        if deals_exist == 0:
            for title, cemail, amount, stage, prob, memail, offset, source in DEALS:
                client = clients_by_email.get(cemail.lower())
                if client is None:
                    continue
                mgr = users_by_email.get(memail)
                db.add(
                    Deal(
                        title=title, client_id=client.id,
                        manager_id=mgr.id if mgr else None, amount=amount, currency="UAH",
                        stage=stage, source=source, probability=prob,
                        deadline=today + timedelta(days=offset),
                    )
                )
                db.flush()
                db.add(
                    Activity(
                        client_id=client.id, actor_id=mgr.id if mgr else None,
                        type="deal_created",
                        message=f"Deal '{title}' created at stage {stage.value} (seed)",
                    )
                )

        tasks_exist = db.scalar(select(func.count(Task.id))) or 0
        if tasks_exist == 0:
            for title, desc, prio, tstatus, cemail, aemail, offset in TASKS:
                client = clients_by_email.get(cemail.lower())
                assignee = users_by_email.get(aemail)
                db.add(
                    Task(
                        title=title, description=desc, priority=prio, status=tstatus,
                        client_id=client.id if client else None,
                        assignee_id=assignee.id if assignee else None,
                        due_date=today + timedelta(days=offset),
                    )
                )

        tickets_exist = db.scalar(select(func.count(Ticket.id))) or 0
        if tickets_exist == 0:
            for title, desc, prio, tstatus, cemail, aemail, first_msg in TICKETS:
                client = clients_by_email.get(cemail.lower())
                assignee = users_by_email.get(aemail)
                ticket = Ticket(
                    title=title, description=desc, priority=prio, status=tstatus,
                    client_id=client.id if client else None,
                    assignee_id=assignee.id if assignee else None,
                    closed_at=datetime.utcnow() if tstatus == TicketStatus.closed else None,
                )
                db.add(ticket)
                db.flush()
                db.add(
                    TicketMessage(
                        ticket_id=ticket.id,
                        author_id=assignee.id if assignee else None,
                        body=first_msg,
                    )
                )

        db.commit()
        print("Seed complete. Demo login: admin@crmpro.example / " + DEMO_PASSWORD)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_admin(email: str, password: str, full_name: str = "Administrator") -> None:
    """Create (or reset the password of) an admin user. Idempotent by email."""
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    db: Session = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            user = User(
                email=email.lower(), full_name=full_name,
                hashed_password=hash_password(password), role=UserRole.admin,
            )
            db.add(user)
            print(f"Admin user created: {email}")
        else:
            user.hashed_password = hash_password(password)
            user.role = UserRole.admin
            user.is_active = True
            db.add(user)
            print(f"Admin password reset for existing user: {email}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRMPro database utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed", help="Insert idempotent demo data")

    p_admin = sub.add_parser("create-admin", help="Create or reset an admin user")
    p_admin.add_argument("--email", required=True)
    p_admin.add_argument("--password", required=True)
    p_admin.add_argument("--name", default="Administrator")

    args = parser.parse_args()
    if args.command == "seed":
        seed()
    elif args.command == "create-admin":
        create_admin(args.email, args.password, args.name)


