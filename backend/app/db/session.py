"""Database engine, session factory and FastAPI dependency.

A single engine is created per process. Sessions are per-request via the
``get_db`` dependency. SQLite needs ``check_same_thread=False`` because
FastAPI serves requests from a thread pool.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if settings.is_sqlite:
    connect_args = {"check_same_thread": False}
    # SQLite + NullPool avoids "database is locked" surprises under tests.
    engine_kwargs["connect_args"] = connect_args

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
