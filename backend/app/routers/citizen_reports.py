import random
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/citizen-reports", tags=["citizen-reports"])


def generate_tracking_id(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(models.CitizenReport).count() + 1
    return f"TRK-{year}-{count:05d}"


def generate_case_id(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(models.Case).count() + 101
    return f"CASE-{year}-{count:05d}"


def run_ai_processing(description: str, crime_type: str, evidence_list: List[dict]):
    desc_lower = description.lower()
    type_lower = crime_type.lower()
    
    # Priority AI logic
    if any(k in desc_lower or k in type_lower for k in ["gun", "weapon", "murder", "assault", "kidnap", "extortion", "bomb", "armed", "cctv"]):
        priority = "critical"
    elif any(k in desc_lower or k in type_lower for k in ["robbery", "stolen", "car", "vehicle", "cyber", "fraud", "scam", "lakh"]):
        priority = "high"
    elif any(k in desc_lower or k in type_lower for k in ["theft", "burglary", "snatching", "harassment"]):
        priority = "medium"
    else:
        priority = "low"

    # AI Summary generation
    ev_summary = f"{len(evidence_list)} evidence file(s) attached" if evidence_list else "No media evidence attached"
    ai_summary = (
        f"AI Analysis: Incident categorized under '{crime_type}'. "
        f"Assigned priority: {priority.upper()}. {ev_summary}. "
        f"Key details identified: {description[:120]}... "
        f"Recommended Action: High-priority dispatch and verification by local patrol unit."
    )

    return {
        "ai_classification": crime_type,
        "ai_priority": priority,
        "ai_summary": ai_summary
    }


@router.post("", response_model=schemas.CitizenReportOut)
def create_citizen_report(
    report_in: schemas.CitizenReportCreate,
    db: Session = Depends(get_db)
):
    tracking_id = generate_tracking_id(db)
    incident_date = report_in.incident_date or datetime.utcnow()

    # Evidence processing
    evidence_dicts = [ev.model_dump() for ev in (report_in.evidence or [])]
    ai_res = run_ai_processing(report_in.description, report_in.crime_type, evidence_dicts)

    db_report = models.CitizenReport(
        id=str(uuid.uuid4()),
        tracking_id=tracking_id,
        crime_type=report_in.crime_type,
        incident_date=incident_date,
        location=report_in.location,
        latitude=report_in.latitude or 25.5941,
        longitude=report_in.longitude or 85.1376,
        description=report_in.description,
        reporter_name=report_in.reporter_name,
        reporter_phone=report_in.reporter_phone,
        reporter_email=report_in.reporter_email,
        status="pending",
        ai_classification=ai_res["ai_classification"],
        ai_priority=ai_res["ai_priority"],
        ai_summary=ai_res["ai_summary"],
        created_at=datetime.utcnow()
    )
    db.add(db_report)
    db.flush()

    if report_in.evidence:
        for ev in report_in.evidence:
            db_ev = models.ReportEvidence(
                id=str(uuid.uuid4()),
                report_id=db_report.id,
                file_name=ev.file_name,
                file_type=ev.file_type,
                file_path=ev.file_path or f"/uploads/evidence/{ev.file_name}",
                created_at=datetime.utcnow()
            )
            db.add(db_ev)

    db.commit()
    db.refresh(db_report)
    return db_report


@router.get("/track/{tracking_id}", response_model=schemas.CitizenReportOut)
def track_report(tracking_id: str, db: Session = Depends(get_db)):
    report = db.query(models.CitizenReport).options(
        joinedload(models.CitizenReport.evidence_items)
    ).filter(
        models.CitizenReport.tracking_id == tracking_id.strip()
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found with given Tracking ID")
    return report


@router.get("", response_model=List[schemas.CitizenReportOut])
def list_citizen_reports(
    status: Optional[str] = Query(None, description="Filter status: pending, verified, rejected"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.CitizenReport).options(joinedload(models.CitizenReport.evidence_items))
    if status:
        query = query.filter(models.CitizenReport.status == status)
    return query.order_by(models.CitizenReport.created_at.desc()).all()


@router.get("/{report_id}", response_model=schemas.CitizenReportOut)
def get_citizen_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    report = db.query(models.CitizenReport).options(
        joinedload(models.CitizenReport.evidence_items)
    ).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Citizen report not found")
    return report


@router.post("/{report_id}/verify", response_model=schemas.CitizenReportOut)
def verify_citizen_report(
    report_id: str,
    verify_in: schemas.CitizenReportVerify,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Citizen report not found")

    if verify_in.action.lower() == "approve":
        report.status = "verified"
        report.reviewed_by_user_id = current_user.id
        report.reviewed_at = datetime.utcnow()

        # Create Official Case
        case_id_str = generate_case_id(db)
        sev_map = {
            "critical": models.Severity.critical,
            "high": models.Severity.high,
            "medium": models.Severity.medium,
            "low": models.Severity.low
        }
        severity_val = sev_map.get((report.ai_priority or "medium").lower(), models.Severity.medium)

        new_case = models.Case(
            id=str(uuid.uuid4()),
            case_id=case_id_str,
            title=f"[Citizen Report] {report.crime_type} - {report.location}",
            crime_type=report.crime_type,
            district="Central District",
            station_name="TRACE Citizen Verification Station",
            status=models.CaseStatus.open,
            severity=severity_val,
            incident_date=report.incident_date,
            latitude=report.latitude,
            longitude=report.longitude,
            summary=f"Citizen Report (Tracking ID: {report.tracking_id})\nReporter: {report.reporter_name} ({report.reporter_phone})\n\nDescription: {report.description}\n\nAI Summary: {report.ai_summary or 'N/A'}",
            created_at=datetime.utcnow()
        )
        db.add(new_case)
        db.flush()

        report.created_case_id = new_case.id

        # Notify Officers
        notification = models.Notification(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            type="case_assigned",
            title=f"Case Created from Citizen Report {report.tracking_id}",
            message=f"Case {case_id_str} has been created and integrated into TRACE Engine after verification.",
            related_case_id=new_case.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notification)

    elif verify_in.action.lower() == "reject":
        report.status = "rejected"
        report.rejection_reason = verify_in.rejection_reason or "Report rejected after officer verification."
        report.reviewed_by_user_id = current_user.id
        report.reviewed_at = datetime.utcnow()
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'.")

    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/analyze-ai", response_model=schemas.CitizenReportOut)
def analyze_report_ai(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    report = db.query(models.CitizenReport).options(
        joinedload(models.CitizenReport.evidence_items)
    ).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Citizen report not found")

    ev_list = [{"file_name": e.file_name, "file_type": e.file_type} for e in report.evidence_items]
    ai_res = run_ai_processing(report.description, report.crime_type, ev_list)

    report.ai_classification = ai_res["ai_classification"]
    report.ai_priority = ai_res["ai_priority"]
    report.ai_summary = ai_res["ai_summary"]

    db.commit()
    db.refresh(report)
    return report
