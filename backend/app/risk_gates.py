"""
Risk Gates Protocol & Intake Validation Layer.

Executes mandatory verification checks before any business logic is executed:
1. Auth & Active User Status
2. Role Authorization (RBAC)
3. Entity Existence & Ownership
4. Duplicate Action / Idempotency Checks
5. Valid State Transitions
6. Business Rule & Constraint Enforcement
7. Automation & AI Safety Controls
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from app import models, schemas
from app.errors import (
    AuthenticationError, AuthorizationError, ResourceNotFoundError,
    ConflictError, BusinessRuleError, ValidationError
)


def check_authentication_and_active(user: Optional[models.User]) -> models.User:
    if not user:
        raise AuthenticationError("Authentication credentials were not provided or are invalid")
    if not user.is_active:
        raise AuthorizationError("User account has been deactivated")
    return user


def check_role_authorization(user: models.User, allowed_roles: List[models.RoleEnum]) -> None:
    check_authentication_and_active(user)
    if user.role not in allowed_roles:
        roles_str = ", ".join([r.value for r in allowed_roles])
        raise AuthorizationError(f"Access denied. Requires one of roles: [{roles_str}]")


def check_case_creation_gate(db: Session, payload: schemas.CaseCreate, user: models.User) -> None:
    check_role_authorization(user, [models.RoleEnum.investigator, models.RoleEnum.admin])
    
    # Duplicate check
    existing = db.query(models.Case).filter(models.Case.case_id == payload.case_id).first()
    if existing:
        raise ConflictError(f"A case with case_id '{payload.case_id}' already exists")
    
    # Date sanity check
    max_future = datetime.now(timezone.utc) + timedelta(hours=1)
    if payload.incident_date.tzinfo is None:
        incident_dt = payload.incident_date.replace(tzinfo=timezone.utc)
    else:
        incident_dt = payload.incident_date

    if incident_dt > max_future:
        raise BusinessRuleError("incident_date cannot be set in the future")
        
    # Coordinate range check
    if payload.latitude is not None and not (-90.0 <= payload.latitude <= 90.0):
        raise ValidationError("latitude must be between -90.0 and 90.0")
    if payload.longitude is not None and not (-180.0 <= payload.longitude <= 180.0):
        raise ValidationError("longitude must be between -180.0 and 180.0")


def check_citizen_report_submission_gate(payload: schemas.CitizenReportCreate) -> None:
    if not payload.crime_type.strip():
        raise ValidationError("crime_type is required and cannot be blank")
    if not payload.location.strip():
        raise ValidationError("location is required and cannot be blank")
    if not payload.description.strip() or len(payload.description.strip()) < 10:
        raise ValidationError("description must be at least 10 characters long")
    if not payload.reporter_name.strip():
        raise ValidationError("reporter_name is required and cannot be blank")
    if not payload.reporter_phone.strip() or len(payload.reporter_phone.strip()) < 5:
        raise ValidationError("reporter_phone must contain a valid contact number")

    if payload.latitude is not None and not (-90.0 <= payload.latitude <= 90.0):
        raise ValidationError("latitude must be between -90.0 and 90.0")
    if payload.longitude is not None and not (-180.0 <= payload.longitude <= 180.0):
        raise ValidationError("longitude must be between -180.0 and 180.0")


def check_citizen_report_verification_gate(
    db: Session, report_id: str, payload: schemas.CitizenReportVerify, user: models.User
) -> models.CitizenReport:
    check_role_authorization(user, [models.RoleEnum.investigator, models.RoleEnum.analyst, models.RoleEnum.admin])
    
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise ResourceNotFoundError(f"Citizen report with ID '{report_id}' was not found")

    # State transition check
    if report.status != "pending":
        raise ConflictError(f"Citizen report has already been reviewed (current status: '{report.status}')")

    if payload.action not in ("approve", "reject"):
        raise ValidationError("Action must be either 'approve' or 'reject'")

    if payload.action == "reject" and (not payload.rejection_reason or not payload.rejection_reason.strip()):
        raise ValidationError("A non-empty rejection_reason is required when rejecting a report")

    return report


def check_task_transition_gate(
    db: Session, task: models.CaseTask, payload: schemas.TaskUpdate, user: models.User
) -> None:
    check_authentication_and_active(user)

    if payload.status:
        valid_statuses = ("todo", "in_progress", "done")
        if payload.status not in valid_statuses:
            raise ValidationError(f"Invalid task status '{payload.status}'. Must be one of: {', '.join(valid_statuses)}")

    if payload.assigned_to_user_id:
        target_user = db.query(models.User).filter(models.User.id == payload.assigned_to_user_id).first()
        if not target_user:
            raise ResourceNotFoundError(f"Assigned user ID '{payload.assigned_to_user_id}' does not exist")
        if not target_user.is_active:
            raise BusinessRuleError("Cannot assign tasks to a deactivated user account")


def check_assignment_gate(
    db: Session, case_id: str, assigned_to_user_id: str, user: models.User
) -> models.User:
    check_role_authorization(user, [models.RoleEnum.investigator, models.RoleEnum.analyst, models.RoleEnum.admin])

    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise ResourceNotFoundError(f"Case with ID '{case_id}' was not found")

    target_user = db.query(models.User).filter(models.User.id == assigned_to_user_id).first()
    if not target_user:
        raise ResourceNotFoundError(f"Target user ID '{assigned_to_user_id}' was not found")
    if not target_user.is_active:
        raise BusinessRuleError("Cannot assign cases to an inactive user account")

    return target_user


def check_agent_action_gate(db: Session, action_id: str, user: models.User) -> models.PendingAgentAction:
    check_authentication_and_active(user)
    
    action = db.query(models.PendingAgentAction).filter(models.PendingAgentAction.id == action_id).first()
    if not action:
        raise ResourceNotFoundError(f"Pending agent action '{action_id}' was not found")

    if action.status != "pending":
        raise ConflictError(f"Agent action has already been processed (current status: '{action.status}')")

    return action


def check_user_admin_gate(
    db: Session, target_user_id: Optional[str], new_email: Optional[str], is_active_change: Optional[bool], current_user: models.User
) -> None:
    check_role_authorization(current_user, [models.RoleEnum.admin])

    if target_user_id and target_user_id == current_user.id and is_active_change is False:
        raise BusinessRuleError("Super Admin users cannot deactivate their own accounts")

    if new_email:
        query = db.query(models.User).filter(models.User.email == new_email)
        if target_user_id:
            query = query.filter(models.User.id != target_user_id)
        if query.first():
            raise ConflictError(f"A user with email '{new_email}' is already registered")


def check_financial_transaction_gate(db: Session, payload: schemas.FinancialTransactionCreate) -> None:
    from_acc = db.query(models.FinancialAccount).filter(models.FinancialAccount.id == payload.from_account_id).first()
    if not from_acc:
        raise ResourceNotFoundError(f"Source account ID '{payload.from_account_id}' was not found")

    to_acc = db.query(models.FinancialAccount).filter(models.FinancialAccount.id == payload.to_account_id).first()
    if not to_acc:
        raise ResourceNotFoundError(f"Target account ID '{payload.to_account_id}' was not found")

    if payload.from_account_id == payload.to_account_id:
        raise BusinessRuleError("Source and target financial accounts must be different")

    if payload.amount <= 0:
        raise ValidationError("Transaction amount must be strictly greater than zero")


def check_fir_details_gate(db: Session, case_id: str, payload: schemas.CaseFIRDetailsCreate) -> models.Case:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise ResourceNotFoundError(f"Case with ID '{case_id}' was not found")

    if payload.crime_no:
        existing_fir = (
            db.query(models.CaseFIRDetails)
            .filter(models.CaseFIRDetails.crime_no == payload.crime_no, models.CaseFIRDetails.case_id != case_id)
            .first()
        )
        if existing_fir:
            raise ConflictError(f"FIR Crime No '{payload.crime_no}' is already registered to another case")

    if payload.incident_from_date and payload.incident_to_date:
        if payload.incident_from_date > payload.incident_to_date:
            raise BusinessRuleError("incident_from_date cannot be later than incident_to_date")

    return case
