"""User management endpoints (admin-only for list/create/update/delete)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.models import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.id)).all()
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserOut:
    email = payload.email.lower()
    exists = db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = User(
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        new_email = data["email"].lower()
        if new_email != user.email:
            clash = db.scalar(select(User).where(User.email == new_email))
            if clash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
                )
        user.email = new_email
    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data["password"])
    for field in ("full_name", "role", "is_active"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete yourself"
        )
    # Guard: do not allow deleting the last remaining admin.
    if user.role.value == "admin":
        admin_count = db.scalar(
            select(User).where(User.role == "admin", User.is_active.is_(True))
        )
        # count via len of scalars for portability
        admins = db.scalars(
            select(User).where(User.role == "admin", User.is_active.is_(True))
        ).all()
        if len(admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last administrator",
            )
    db.delete(user)
    db.commit()
