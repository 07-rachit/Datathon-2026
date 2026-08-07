from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api", tags=["collaboration"])


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def _get_case_or_404(db: Session, case_id: str) -> models.Case:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _format_comment_out(comment: models.CaseComment) -> schemas.CommentOut:
    return schemas.CommentOut(
        id=comment.id,
        case_id=comment.case_id,
        author_user_id=comment.author_user_id,
        author_name=comment.author.name if comment.author else "Unknown",
        author_role=comment.author.role.value if comment.author and comment.author.role else None,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.get("/users/officers")
def list_officers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve list of active officers/users for assignment picker."""
    users = db.query(models.User).filter(models.User.is_active == True).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value if u.role else "viewer",
        }
        for u in users
    ]



def _format_assignment_out(assignment: models.CaseAssignment) -> schemas.AssignmentOut:
    return schemas.AssignmentOut(
        id=assignment.id,
        case_id=assignment.case_id,
        assigned_to_user_id=assignment.assigned_to_user_id,
        assigned_to_name=assignment.assigned_to.name if assignment.assigned_to else "Unknown",
        assigned_to_email=assignment.assigned_to.email if assignment.assigned_to else None,
        assigned_by_user_id=assignment.assigned_by_user_id,
        assigned_by_name=assignment.assigned_by.name if assignment.assigned_by else "Unknown",
        role_on_case=assignment.role_on_case,
        assigned_at=assignment.assigned_at,
        status=assignment.status,
    )


def _format_task_out(task: models.CaseTask) -> schemas.TaskOut:
    return schemas.TaskOut(
        id=task.id,
        case_id=task.case_id,
        case_code=task.case.case_id if task.case else None,
        case_title=task.case.title if task.case else None,
        case_severity=task.case.severity.value if task.case and task.case.severity else None,
        title=task.title,
        description=task.description,
        assigned_to_user_id=task.assigned_to_user_id,
        assigned_to_name=task.assigned_to.name if task.assigned_to else None,
        created_by_user_id=task.created_by_user_id,
        created_by_name=task.created_by.name if task.created_by else "Unknown",
        due_date=task.due_date,
        status=task.status,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


# ─── 1. CASE COMMENTS ENDPOINTS ───────────────────────────────────────────────

@router.get("/cases/{case_id}/comments", response_model=List[schemas.CommentOut])
def list_case_comments(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _get_case_or_404(db, case_id)
    comments = (
        db.query(models.CaseComment)
        .filter(models.CaseComment.case_id == case_id)
        .order_by(models.CaseComment.created_at.asc())
        .all()
    )
    return [_format_comment_out(c) for c in comments]


@router.post("/cases/{case_id}/comments", response_model=schemas.CommentOut)
def create_case_comment(
    case_id: str,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    _get_case_or_404(db, case_id)
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Comment content cannot be empty")

    comment = models.CaseComment(
        case_id=case_id,
        author_user_id=current_user.id,
        content=payload.content.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _format_comment_out(comment)


@router.delete("/cases/{case_id}/comments/{comment_id}")
def delete_case_comment(
    case_id: str,
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    comment = db.query(models.CaseComment).filter(
        models.CaseComment.id == comment_id,
        models.CaseComment.case_id == case_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if current_user.role == models.RoleEnum.investigator and comment.author_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted successfully"}


# ─── 2. OFFICER ASSIGNMENTS ENDPOINTS ────────────────────────────────────────

@router.get("/cases/{case_id}/assignments", response_model=List[schemas.AssignmentOut])
def list_case_assignments(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _get_case_or_404(db, case_id)
    assignments = (
        db.query(models.CaseAssignment)
        .filter(models.CaseAssignment.case_id == case_id, models.CaseAssignment.status == "active")
        .order_by(models.CaseAssignment.assigned_at.desc())
        .all()
    )
    return [_format_assignment_out(a) for a in assignments]


from app.websocket import create_and_dispatch_notification


@router.post("/cases/{case_id}/assignments", response_model=schemas.AssignmentOut)
async def create_case_assignment(
    case_id: str,
    payload: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    case = _get_case_or_404(db, case_id)

    # RBAC Enforcement: Investigators can only self-assign
    if current_user.role == models.RoleEnum.investigator and payload.assigned_to_user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Investigators can only self-claim cases"
        )

    target_user = db.query(models.User).filter(models.User.id == payload.assigned_to_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user to assign not found")

    # Check if assignment exists
    existing = db.query(models.CaseAssignment).filter(
        models.CaseAssignment.case_id == case_id,
        models.CaseAssignment.assigned_to_user_id == payload.assigned_to_user_id
    ).first()

    if existing:
        existing.status = "active"
        existing.role_on_case = payload.role_on_case
        existing.assigned_by_user_id = current_user.id
        existing.assigned_at = datetime.utcnow()
        assignment = existing
    else:
        assignment = models.CaseAssignment(
            case_id=case_id,
            assigned_to_user_id=payload.assigned_to_user_id,
            assigned_by_user_id=current_user.id,
            role_on_case=payload.role_on_case,
            status="active",
        )
        db.add(assignment)

    # Audit log entry
    log = models.AuditLog(
        user_id=current_user.id,
        action="case_assignment_change",
        detail=f"Assigned officer {target_user.name} ({payload.role_on_case}) to case {case.case_id}"
    )
    db.add(log)

    db.commit()
    db.refresh(assignment)

    # Sprint 7: Case assignment notification dispatch
    await create_and_dispatch_notification(
        db=db,
        user_id=payload.assigned_to_user_id,
        notification_type="case_assigned",
        title=f"📋 Assigned to Case: {case.case_id}",
        message=f"You were assigned as '{payload.role_on_case}' on case '{case.title}' ({case.district}).",
        related_case_id=case.id,
    )

    return _format_assignment_out(assignment)



@router.delete("/cases/{case_id}/assignments/{assignment_id}")
def remove_case_assignment(
    case_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    case = _get_case_or_404(db, case_id)
    assignment = db.query(models.CaseAssignment).filter(
        models.CaseAssignment.id == assignment_id,
        models.CaseAssignment.case_id == case_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user.role == models.RoleEnum.investigator and assignment.assigned_to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Investigators can only remove their own assignment")

    assignment.status = "removed"

    log = models.AuditLog(
        user_id=current_user.id,
        action="case_assignment_change",
        detail=f"Removed officer assignment for case {case.case_id}"
    )
    db.add(log)

    db.commit()
    return {"message": "Assignment removed successfully"}


# ─── 3. CASE TASKS ENDPOINTS ──────────────────────────────────────────────────

@router.get("/cases/{case_id}/tasks", response_model=List[schemas.TaskOut])
def list_case_tasks(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _get_case_or_404(db, case_id)
    tasks = (
        db.query(models.CaseTask)
        .filter(models.CaseTask.case_id == case_id)
        .order_by(models.CaseTask.created_at.desc())
        .all()
    )
    return [_format_task_out(t) for t in tasks]


@router.post("/cases/{case_id}/tasks", response_model=schemas.TaskOut)
async def create_case_task(
    case_id: str,
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    case = _get_case_or_404(db, case_id)
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Task title cannot be empty")

    task = models.CaseTask(
        case_id=case_id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        assigned_to_user_id=payload.assigned_to_user_id,
        created_by_user_id=current_user.id,
        due_date=payload.due_date,
        status="todo",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Sprint 7: Task assignment notification dispatch
    if task.assigned_to_user_id:
        await create_and_dispatch_notification(
            db=db,
            user_id=task.assigned_to_user_id,
            notification_type="task_assigned",
            title=f"📌 New Task Assigned: {case.case_id}",
            message=f"Task '{task.title}' assigned to you on case '{case.title}'.",
            related_case_id=case.id,
        )

    return _format_task_out(task)



@router.patch("/cases/{case_id}/tasks/{task_id}", response_model=schemas.TaskOut)
def update_case_task(
    case_id: str,
    task_id: str,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    case = _get_case_or_404(db, case_id)
    task = db.query(models.CaseTask).filter(
        models.CaseTask.id == task_id,
        models.CaseTask.case_id == case_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Status update permission check
    if payload.status and payload.status != task.status:
        if current_user.role == models.RoleEnum.investigator:
            if task.assigned_to_user_id != current_user.id and task.created_by_user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Only the assigned officer or creator can update task status"
                )

        old_status = task.status
        task.status = payload.status
        if payload.status == "done":
            task.completed_at = datetime.utcnow()
        elif old_status == "done":
            task.completed_at = None

        log = models.AuditLog(
            user_id=current_user.id,
            action="case_task_status_change",
            detail=f"Task '{task.title}' status changed from '{old_status}' to '{payload.status}' on case {case.case_id}"
        )
        db.add(log)

    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.description is not None:
        task.description = payload.description.strip()
    if payload.assigned_to_user_id is not None:
        task.assigned_to_user_id = payload.assigned_to_user_id
    if payload.due_date is not None:
        task.due_date = payload.due_date

    db.commit()
    db.refresh(task)
    return _format_task_out(task)


@router.delete("/cases/{case_id}/tasks/{task_id}")
def delete_case_task(
    case_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    task = db.query(models.CaseTask).filter(
        models.CaseTask.id == task_id,
        models.CaseTask.case_id == case_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role == models.RoleEnum.investigator:
        if task.created_by_user_id != current_user.id and task.assigned_to_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only delete tasks you created or are assigned to")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}


# ─── 4. LOGGED-IN OFFICER WORKSPACE ("MY WORK") ─────────────────────────────

@router.get("/me/tasks", response_model=List[schemas.TaskOut])
def get_my_open_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve all open/pending tasks assigned to the logged-in officer across all cases."""
    tasks = (
        db.query(models.CaseTask)
        .filter(
            models.CaseTask.assigned_to_user_id == current_user.id,
            models.CaseTask.status != "done"
        )
        .order_by(models.CaseTask.due_date.asc().nulls_last(), models.CaseTask.created_at.desc())
        .all()
    )
    return [_format_task_out(t) for t in tasks]


@router.get("/me/assigned-cases")
def get_my_assigned_cases(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve all active cases currently assigned to the logged-in officer."""
    assignments = (
        db.query(models.CaseAssignment)
        .filter(
            models.CaseAssignment.assigned_to_user_id == current_user.id,
            models.CaseAssignment.status == "active"
        )
        .order_by(models.CaseAssignment.assigned_at.desc())
        .all()
    )

    result = []
    for a in assignments:
        case = a.case
        if case:
            result.append({
                "assignment_id": a.id,
                "case_id": case.id,
                "case_code": case.case_id,
                "title": case.title,
                "crime_type": case.crime_type,
                "district": case.district,
                "severity": case.severity.value if case.severity else "medium",
                "status": case.status.value if case.status else "open",
                "role_on_case": a.role_on_case,
                "assigned_at": a.assigned_at,
            })
    return result
