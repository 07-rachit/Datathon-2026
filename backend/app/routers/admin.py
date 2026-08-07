"""
Admin-only user management endpoints.

All routes require the 'admin' role.
These are the only routes that can create accounts with admin/analyst roles,
since the public /api/auth/signup is restricted to viewer/investigator.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[schemas.UserAdminOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    """Return all users (admin only)."""
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.post("/users", response_model=schemas.UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    """Create a user with any role (admin only). Password must be ≥ 8 chars."""
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)

    log = models.AuditLog(
        user_id=current_user.id,
        action="admin_create_user",
        detail=f"Created user {payload.email} with role {payload.role.value}",
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=schemas.UserAdminOut)
def update_user(
    user_id: str,
    payload: schemas.UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    """Update a user's role, active status, or name (admin only)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id and payload.is_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    changes = []
    if payload.role is not None:
        user.role = payload.role
        changes.append(f"role→{payload.role.value}")
    if payload.is_active is not None:
        user.is_active = payload.is_active
        changes.append(f"active→{payload.is_active}")
    if payload.name is not None:
        user.name = payload.name
        changes.append(f"name→{payload.name}")

    log = models.AuditLog(
        user_id=current_user.id,
        action="admin_update_user",
        detail=f"Updated user {user.email}: {', '.join(changes)}",
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    """Soft-delete (deactivate) a user account (admin only). Does not delete DB row."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    user.is_active = False
    log = models.AuditLog(
        user_id=current_user.id,
        action="admin_deactivate_user",
        detail=f"Deactivated user {user.email}",
    )
    db.add(log)
    db.commit()
