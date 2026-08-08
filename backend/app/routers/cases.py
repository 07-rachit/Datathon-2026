"""
Case management CRUD endpoints and role-scoped query interfaces.

Provides full lifecycle management for security crime cases including creation,
listing with role-aware scoping, detail retrieval, status updates, investigation
label reviews, and phone number masking based on user role (RBAC).
"""
from typing import Optional, Union, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.database import get_db
from app import models, schemas, auth, rag, risk_gates
from app.errors import ResourceNotFoundError
from app.routers import fir as fir_router

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", response_model=schemas.CaseListResponse)
def list_cases(
    q: Optional[str] = Query(None, description="Free text search across case id, title, station"),
    district: Optional[str] = None,
    crime_type: Optional[str] = None,
    status: Optional[models.CaseStatus] = None,
    severity: Optional[models.Severity] = None,
    investigation_label: Optional[models.InvestigationLabelEnum] = None,
    reviewer_id: Optional[str] = None,
    role_scope: Optional[str] = Query(None, description="Role scope filter: admin, investigator, reviewer, authority, hospital, user"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Case)

    effective_scope = (role_scope or "").lower().strip()
    if effective_scope == "investigator":
        query = query.filter(
            or_(
                models.Case.status.in_([models.CaseStatus.open, models.CaseStatus.under_review]),
                models.Case.investigation_label.in_([
                    models.InvestigationLabelEnum.suspected,
                    models.InvestigationLabelEnum.verified,
                    models.InvestigationLabelEnum.needs_review,
                ]),
                models.Case.assignments.any(models.CaseAssignment.assigned_to_user_id == current_user.id),
            )
        )
    elif effective_scope in ["reviewer", "reviewer_authority"]:
        query = query.filter(
            or_(
                models.Case.investigation_label.in_([
                    models.InvestigationLabelEnum.needs_review,
                    models.InvestigationLabelEnum.suspected,
                ]),
                models.Case.reviewer_id == current_user.id,
            )
        )
    elif effective_scope == "authority":
        query = query.filter(
            or_(
                models.Case.severity.in_([models.Severity.high, models.Severity.critical]),
                models.Case.fir_details != None,
            )
        )
    elif effective_scope == "hospital":
        query = query.filter(
            or_(
                models.Case.crime_type.ilike("%Assault%"),
                models.Case.crime_type.ilike("%Murder%"),
                models.Case.crime_type.ilike("%Fraud%"),
                models.Case.severity.in_([models.Severity.high, models.Severity.critical]),
            )
        )
    elif effective_scope == "user":
        query = query.filter(
            or_(
                models.Case.assignments.any(models.CaseAssignment.assigned_to_user_id == current_user.id),
                models.Case.reviewer_id == current_user.id,
                models.Case.status == models.CaseStatus.open,
            )
        )

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Case.case_id.ilike(like),
                models.Case.title.ilike(like),
                models.Case.station_name.ilike(like),
            )
        )
    if district:
        query = query.filter(models.Case.district == district)
    if crime_type:
        query = query.filter(models.Case.crime_type == crime_type)
    if status:
        query = query.filter(models.Case.status == status)
    if severity:
        query = query.filter(models.Case.severity == severity)
    if investigation_label:
        query = query.filter(models.Case.investigation_label == investigation_label)
    if reviewer_id:
        query = query.filter(models.Case.reviewer_id == reviewer_id)
    if date_from:
        query = query.filter(models.Case.incident_date >= date_from)
    if date_to:
        query = query.filter(models.Case.incident_date <= date_to)

    total = query.count()
    results = (
        query.order_by(models.Case.incident_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return schemas.CaseListResponse(
        total=total,
        page=page,
        page_size=page_size,
        active_role_scope=effective_scope or "all",
        results=results,
    )


@router.get("/map", response_model=list[schemas.MapCase])
def map_cases(
    district: Optional[str] = None,
    crime_type: Optional[str] = None,
    status: Optional[models.CaseStatus] = None,
    severity: Optional[models.Severity] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Case).filter(
        models.Case.latitude.isnot(None), models.Case.longitude.isnot(None)
    )
    if district:
        query = query.filter(models.Case.district == district)
    if crime_type:
        query = query.filter(models.Case.crime_type == crime_type)
    if status:
        query = query.filter(models.Case.status == status)
    if severity:
        query = query.filter(models.Case.severity == severity)
    return query.all()



@router.get("/{case_id}")
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    base_dict = {
        col: getattr(case, col)
        for col in [
            "id", "case_id", "title", "crime_type", "district", "station_name",
            "status", "severity", "incident_date", "latitude", "longitude",
            "summary", "created_at",
        ]
    }

    # Mask phone numbers for viewer-role users
    if current_user.role == models.RoleEnum.viewer:
        base_dict["persons"] = [schemas.PersonOutMasked.mask(p) for p in case.persons]
    else:
        base_dict["persons"] = [schemas.PersonOut.model_validate(p) for p in case.persons]

    base_dict["evidence"] = [schemas.EvidenceOut.model_validate(e) for e in case.evidence]

    # Embedded KSP FIR extensions
    base_dict["fir_details"] = fir_router._build_fir_out(case.fir_details) if case.fir_details else None
    base_dict["complainant"] = fir_router._build_complainant_out(case.complainant, current_user, db) if case.complainant else None
    base_dict["arrest_events"] = [fir_router._build_arrest_out(e) for e in case.arrest_events]
    base_dict["act_sections"] = [fir_router._build_act_section_out(a) for a in case.act_sections]
    base_dict["chargesheet"] = fir_router._build_cs_out(case.chargesheet) if case.chargesheet else None

    return base_dict


@router.get("/{case_id}/timeline")
def get_case_timeline(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    events: List[Dict[str, Any]] = []

    # 1. Incident Occurred
    if case.incident_date:
        events.append({
            "date": case.incident_date,
            "event_type": "incident_occurred",
            "label": f"Incident Occurred: {case.title}",
            "actor": case.station_name,
            "reference_id": case.case_id,
        })

    # 2. FIR Details Timestamps
    fir = case.fir_details
    if fir:
        if fir.info_received_ps_date:
            events.append({
                "date": fir.info_received_ps_date,
                "event_type": "info_received",
                "label": "Information Received at Police Station",
                "actor": fir.police_station.unit_name if fir.police_station else case.station_name,
                "reference_id": fir.crime_no,
            })
        if fir.crime_registered_date:
            events.append({
                "date": fir.crime_registered_date,
                "event_type": "fir_registered",
                "label": f"FIR Formally Registered (Crime No: {fir.crime_no})",
                "actor": fir.registering_officer.name if fir.registering_officer else "Registering Officer",
                "reference_id": fir.crime_no,
            })

    # 3. Arrest / Surrender Events
    for arr in case.arrest_events:
        acc_name = arr.accused_person.name if arr.accused_person else "Suspect"
        officer = arr.investigating_officer.name if arr.investigating_officer else "Investigating Officer"
        events.append({
            "date": arr.event_date,
            "event_type": arr.event_type.lower(),
            "label": f"{arr.event_type.capitalize()} Event: {acc_name}",
            "actor": officer,
            "reference_id": arr.id,
        })

    # 4. Chargesheet Details
    cs = case.chargesheet
    if cs and cs.chargesheet_date:
        officer = cs.filing_officer.name if cs.filing_officer else "Filing Officer"
        events.append({
            "date": cs.chargesheet_date,
            "event_type": "chargesheet_filed",
            "label": f"Chargesheet Filed (Type {cs.cs_type})",
            "actor": officer,
            "reference_id": cs.id,
        })

    # 5. Audit Log Case Actions
    audit_logs = db.query(models.AuditLog).filter(
        models.AuditLog.detail.ilike(f"%{case.case_id}%")
    ).all()
    for log in audit_logs:
        events.append({
            "date": log.created_at,
            "event_type": "audit_action",
            "label": f"Action Logged: {log.action}",
            "actor": f"User ID: {log.user_id}" if log.user_id else "System",
            "reference_id": log.id,
        })

    # Sort chronologically
    events.sort(key=lambda x: x["date"])
    return events


@router.get("/{case_id}/similar")
def similar_cases(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not rag._chunks:
        rag.build_index(db)

    hits = rag.similar_to_case(case_id, top_k=4)
    results = []
    for chunk, score in hits:
        similar = db.query(models.Case).filter(models.Case.id == chunk.case_id).first()
        if similar:
            results.append({
                "id": similar.id,
                "case_id": similar.case_id,
                "title": similar.title,
                "district": similar.district,
                "crime_type": similar.crime_type,
                "severity": similar.severity.value,
                "status": similar.status.value,
                "similarity": round(score, 3),
            })
    return results


import asyncio
from app.database import SessionLocal
from app import proactive_agent
from app.websocket import broadcast_notification_to_roles


@router.post("", response_model=schemas.CaseOut)
async def create_case(
    payload: schemas.CaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    risk_gates.check_case_creation_gate(db, payload, current_user)

    case = models.Case(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)

    log = models.AuditLog(user_id=current_user.id, action="create_case", detail=f"Created case {case.case_id}")
    db.add(log)
    db.commit()

    rag.build_index(db)

    # Sprint 7: High-severity case notification dispatch
    if case.severity in (models.Severity.high, models.Severity.critical):
        await broadcast_notification_to_roles(
            db=db,
            roles=[models.RoleEnum.investigator, models.RoleEnum.analyst, models.RoleEnum.admin],
            notification_type="high_severity_case",
            title=f"🚨 High Severity Incident Logged: {case.case_id}",
            message=f"New {case.severity.value.upper()} severity incident '{case.title}' reported in {case.district} ({case.station_name}).",
            related_case_id=case.id,
            exclude_user_id=current_user.id,
        )

        # Sprint 8: Trigger proactive AI background analysis (asynchronous background task)
        asyncio.create_task(proactive_agent.trigger_proactive_case_analysis_task(case.id, SessionLocal))

    return case


# ── Security Case Investigation Review & Labels Endpoints ────────────────────

@router.get("/{case_id}/investigation", response_model=schemas.CaseInvestigationStatusOut)
def get_case_investigation_status(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        case = db.query(models.Case).filter(models.Case.case_id == case_id).first()
    if not case:
        raise ResourceNotFoundError(f"Case with ID '{case_id}' was not found")

    history = (
        db.query(models.CaseInvestigationHistory)
        .filter(models.CaseInvestigationHistory.case_id == case.id)
        .order_by(models.CaseInvestigationHistory.created_at.desc())
        .all()
    )

    current_label_val = case.investigation_label.value if hasattr(case.investigation_label, "value") else str(case.investigation_label or "Unreviewed")

    return schemas.CaseInvestigationStatusOut(
        case_id=case.id,
        current_label=current_label_val,
        investigator_note=case.investigator_note,
        reviewer_id=case.reviewer_id,
        reviewer_name=case.reviewer_name,
        review_timestamp=case.review_timestamp,
        previous_label=case.previous_investigation_label,
        history=history,
    )


@router.put("/{case_id}/investigation", response_model=schemas.CaseInvestigationStatusOut)
def update_case_investigation_label(
    case_id: str,
    payload: schemas.CaseInvestigationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    case = risk_gates.check_investigation_label_update_gate(db, case_id, payload, current_user)

    prev_label = case.investigation_label.value if hasattr(case.investigation_label, "value") else str(case.investigation_label or "Unreviewed")
    new_label_val = payload.label.value if hasattr(payload.label, "value") else str(payload.label)

    note_clean = payload.note.strip()
    now = datetime.utcnow()

    # Update case fields
    case.previous_investigation_label = prev_label
    case.investigation_label = payload.label
    case.investigator_note = note_clean
    case.reviewer_id = current_user.id
    case.reviewer_name = current_user.name
    case.review_timestamp = now
    case.updated_at = now

    # Create immutable history record
    hist_entry = models.CaseInvestigationHistory(
        case_id=case.id,
        previous_label=prev_label,
        new_label=new_label_val,
        investigator_note=note_clean,
        reviewer_id=current_user.id,
        reviewer_name=current_user.name,
        created_at=now,
    )
    db.add(hist_entry)

    # Record Audit Log
    audit_entry = models.AuditLog(
        user_id=current_user.id,
        action="update_investigation_label",
        detail=f"Updated investigation label for case {case.case_id} from '{prev_label}' to '{new_label_val}'. Note: {note_clean[:80]}",
    )
    db.add(audit_entry)

    db.commit()
    db.refresh(case)

    # Record Activity History
    try:
        from app.activity_logger import record_activity
        record_activity(
            db=db,
            user_id=current_user.id,
            user_name=current_user.name,
            activity_type="investigation_label_updated",
            module="cases",
            entity_type="Case",
            entity_id=case.id,
            title=f"Investigation Label Updated: {case.case_id}",
            description=f"Label changed from '{prev_label}' to '{new_label_val}' by {current_user.name}.",
            metadata={
                "previous_label": prev_label,
                "new_label": new_label_val,
                "investigator_note": note_clean,
                "reviewer_id": current_user.id,
                "reviewer_name": current_user.name,
                "case_id": case.case_id,
            },
            status="completed",
            tags=["investigation", "label", new_label_val.lower().replace(" ", "_")],
        )
    except Exception as act_err:
        print(f"--> Activity history record notice: {act_err}")

    history = (
        db.query(models.CaseInvestigationHistory)
        .filter(models.CaseInvestigationHistory.case_id == case.id)
        .order_by(models.CaseInvestigationHistory.created_at.desc())
        .all()
    )

    return schemas.CaseInvestigationStatusOut(
        case_id=case.id,
        current_label=new_label_val,
        investigator_note=case.investigator_note,
        reviewer_id=case.reviewer_id,
        reviewer_name=case.reviewer_name,
        review_timestamp=case.review_timestamp,
        previous_label=case.previous_investigation_label,
        history=history,
    )


