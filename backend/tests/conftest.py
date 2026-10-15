"""Pytest fixtures.

Every test runs against a fresh, isolated in-file SQLite database so tests
never touch the developer's real crmpro.db. The app's engine/session are
monkeypatched to point at the test database, and tables are created from the
ORM metadata (equivalent to running the migrations).
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure a deterministic environment before importing the app.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")

from app.core.security import hash_password  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import models  # noqa: E402,F401  (register tables)
from app.models.models import User, UserRole  # noqa: E402


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session):
    user = User(
        email="admin@example.com",
        full_name="Test Admin",
        hashed_password=hash_password("Admin123!"),
        role=UserRole.admin,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def manager_user(db_session):
    user = User(
        email="manager@example.com",
        full_name="Test Manager",
        hashed_password=hash_password("Manager123!"),
        role=UserRole.manager,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_token(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def manager_token(client, manager_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": "Manager123!"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def manager_headers(manager_token):
    return {"Authorization": f"Bearer {manager_token}"}
