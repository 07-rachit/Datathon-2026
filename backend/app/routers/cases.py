"""
Case management CRUD endpoints.

Provides full lifecycle management for crime cases including creation,
listing with pagination, detail retrieval, status updates, and phone
number masking based on user role (RBAC).
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
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Case)

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

    return schemas.CaseListResponse(total=total, page=page, page_size=page_size, results=results)


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


