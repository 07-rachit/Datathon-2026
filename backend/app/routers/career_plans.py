"""
Career Plans & Learning Search REST Endpoints.

Provides fast, indexed keyword searching, multi-criteria topic, difficulty,
deadline, and goal filtering, sorting, pagination, and full plan management.
"""
from typing import Optional, List
from datetime import datetime
import math

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from app.database import get_db
from app import models, schemas, auth, risk_gates
from app.errors import ResourceNotFoundError, AuthorizationError, ValidationError

router = APIRouter(prefix="/api/career-plans", tags=["career_plans"])


def _to_plan_out(plan: models.CareerPlan) -> schemas.CareerPlanOut:
    owner_name = plan.owner.name if plan.owner else None
    owner_email = plan.owner.email if plan.owner else None
    diff_val = plan.difficulty_level.value if hasattr(plan.difficulty_level, "value") else str(plan.difficulty_level or "Intermediate")
    
    return schemas.CareerPlanOut(
        id=plan.id,
        user_id=plan.user_id,
        title=plan.title,
        description=plan.description,
        topic=plan.topic,
        difficulty_level=diff_val,
        target_goal=plan.target_goal,
        deadline=plan.deadline,
        tags=plan.tags,
        status=plan.status,
        milestones=plan.milestones,
        notes=plan.notes,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        owner_name=owner_name,
        owner_email=owner_email,
    )


@router.get("", response_model=schemas.CareerPlanListResponse)
def list_career_plans(
    q: Optional[str] = Query(None, description="Free text keyword search across title, description, goals, milestones, notes, tags"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level (Beginner, Intermediate, Advanced, Expert)"),
    goal: Optional[str] = Query(None, description="Filter by target goal"),
    status: Optional[str] = Query(None, description="Filter by status (active, completed, archived)"),
    deadline_before: Optional[datetime] = Query(None, description="Filter deadline on or before date"),
    deadline_after: Optional[datetime] = Query(None, description="Filter deadline on or after date"),
    user_id: Optional[str] = Query(None, description="Filter by plan owner user ID"),
    sort_by: str = Query("newest", description="Sort order: newest, oldest, deadline, alphabetical"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    risk_gates.check_career_plan_search_gate(current_user, page, page_size, sort_by)

    query = db.query(models.CareerPlan).options(joinedload(models.CareerPlan.owner))

    # RBAC Scoping: Non-admin/analyst users see their own plans unless explicit user_id requested with permissions
    if current_user.role not in (models.RoleEnum.admin, models.RoleEnum.analyst):
        query = query.filter(models.CareerPlan.user_id == current_user.id)
    elif user_id:
        query = query.filter(models.CareerPlan.user_id == user_id)

    # Keyword search across searchable metadata
    if q and q.strip():
        search_kw = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.CareerPlan.title.ilike(search_kw),
                models.CareerPlan.description.ilike(search_kw),
                models.CareerPlan.topic.ilike(search_kw),
                models.CareerPlan.target_goal.ilike(search_kw),
                models.CareerPlan.tags.ilike(search_kw),
                models.CareerPlan.milestones.ilike(search_kw),
                models.CareerPlan.notes.ilike(search_kw),
            )
        )

    # Topic Filter
    if topic and topic.strip():
        query = query.filter(models.CareerPlan.topic.ilike(topic.strip()))

    # Difficulty Filter
    if difficulty and difficulty.strip():
        query = query.filter(models.CareerPlan.difficulty_level.ilike(difficulty.strip()))

    # Target Goal Filter
    if goal and goal.strip():
        query = query.filter(models.CareerPlan.target_goal.ilike(goal.strip()))

    # Status Filter
    if status and status.strip():
        query = query.filter(models.CareerPlan.status == status.strip().lower())

    # Deadline Filters
    if deadline_before:
        query = query.filter(models.CareerPlan.deadline <= deadline_before)
    if deadline_after:
        query = query.filter(models.CareerPlan.deadline >= deadline_after)

    # Total Count
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    # Sorting
    sort_clean = sort_by.lower().strip()
    if sort_clean == "oldest":
        query = query.order_by(models.CareerPlan.created_at.asc())
    elif sort_clean == "deadline":
        query = query.order_by(models.CareerPlan.deadline.asc().nullslast())
    elif sort_clean == "alphabetical":
        query = query.order_by(models.CareerPlan.title.asc())
    else:  # newest
        query = query.order_by(models.CareerPlan.created_at.desc())

    # Pagination
    plans = query.offset((page - 1) * page_size).limit(page_size).all()
    results = [_to_plan_out(p) for p in plans]

    # Extract distinct facets for dropdowns
    available_topics = [t[0] for t in db.query(models.CareerPlan.topic).distinct().all() if t[0]]
    available_goals = [g[0] for g in db.query(models.CareerPlan.target_goal).distinct().all() if g[0]]
    available_difficulties = ["Beginner", "Intermediate", "Advanced", "Expert"]

    return schemas.CareerPlanListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=results,
        available_topics=sorted(available_topics),
        available_goals=sorted(available_goals),
        available_difficulties=available_difficulties,
    )


@router.get("/{plan_id}", response_model=schemas.CareerPlanOut)
def get_career_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    plan = db.query(models.CareerPlan).options(joinedload(models.CareerPlan.owner)).filter(models.CareerPlan.id == plan_id).first()
    if not plan:
        raise ResourceNotFoundError(f"Career plan with ID '{plan_id}' was not found")

    if current_user.role not in (models.RoleEnum.admin, models.RoleEnum.analyst) and plan.user_id != current_user.id:
        raise AuthorizationError("You do not have permission to view this career plan")

    return _to_plan_out(plan)


@router.post("", response_model=schemas.CareerPlanOut)
def create_career_plan(
    payload: schemas.CareerPlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    diff_val = payload.difficulty_level.value if hasattr(payload.difficulty_level, "value") else str(payload.difficulty_level)

    plan = models.CareerPlan(
        user_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        topic=payload.topic.strip(),
        difficulty_level=diff_val,
        target_goal=payload.target_goal.strip(),
        deadline=payload.deadline,
        tags=payload.tags.strip() if payload.tags else None,
        status=payload.status.strip().lower() if payload.status else "active",
        milestones=payload.milestones.strip() if payload.milestones else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(plan)
    db.commit()

    # Refresh with owner relationship
    plan = db.query(models.CareerPlan).options(joinedload(models.CareerPlan.owner)).filter(models.CareerPlan.id == plan.id).first()
    return _to_plan_out(plan)


@router.put("/{plan_id}", response_model=schemas.CareerPlanOut)
def update_career_plan(
    plan_id: str,
    payload: schemas.CareerPlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    plan = db.query(models.CareerPlan).filter(models.CareerPlan.id == plan_id).first()
    if not plan:
        raise ResourceNotFoundError(f"Career plan with ID '{plan_id}' was not found")

    if current_user.role not in (models.RoleEnum.admin, models.RoleEnum.analyst) and plan.user_id != current_user.id:
        raise AuthorizationError("You do not have permission to update this career plan")

    if payload.title is not None:
        plan.title = payload.title.strip()
    if payload.description is not None:
        plan.description = payload.description.strip() if payload.description else None
    if payload.topic is not None:
        plan.topic = payload.topic.strip()
    if payload.difficulty_level is not None:
        diff_val = payload.difficulty_level.value if hasattr(payload.difficulty_level, "value") else str(payload.difficulty_level)
        plan.difficulty_level = diff_val
    if payload.target_goal is not None:
        plan.target_goal = payload.target_goal.strip()
    if payload.deadline is not None:
        plan.deadline = payload.deadline
    if payload.tags is not None:
        plan.tags = payload.tags.strip() if payload.tags else None
    if payload.status is not None:
        plan.status = payload.status.strip().lower()
    if payload.milestones is not None:
        plan.milestones = payload.milestones.strip() if payload.milestones else None
    if payload.notes is not None:
        plan.notes = payload.notes.strip() if payload.notes else None

    plan.updated_at = datetime.utcnow()
    db.commit()

    plan = db.query(models.CareerPlan).options(joinedload(models.CareerPlan.owner)).filter(models.CareerPlan.id == plan.id).first()
    return _to_plan_out(plan)


@router.delete("/{plan_id}")
def delete_career_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    plan = db.query(models.CareerPlan).filter(models.CareerPlan.id == plan_id).first()
    if not plan:
        raise ResourceNotFoundError(f"Career plan with ID '{plan_id}' was not found")

    if current_user.role not in (models.RoleEnum.admin, models.RoleEnum.analyst) and plan.user_id != current_user.id:
        raise AuthorizationError("You do not have permission to delete this career plan")

    db.delete(plan)
    db.commit()
    return {"status": "success", "message": f"Career plan '{plan_id}' has been deleted"}
