from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, auth

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs")
def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    query = db.query(models.AuditLog, models.User.name, models.User.email).outerjoin(
        models.User, models.AuditLog.user_id == models.User.id
    ).order_by(models.AuditLog.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    results = [
        {
            "id": log.id,
            "action": log.action,
            "detail": log.detail,
            "user_name": name,
            "user_email": email,
            "created_at": log.created_at.isoformat(),
        }
        for log, name, email in rows
    ]
    return {"total": total, "page": page, "page_size": page_size, "results": results}
