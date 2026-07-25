"""
Offender Profiling & Behavioral Risk Scoring Router.

Risk score calculation is STRICTLY BEHAVIORAL (case volume, severity, recency,
MO repetition, network centrality). Demographic attributes are EXCLUDED.
See RISK_SCORING.md for complete mathematical details.

Access: investigator, analyst, admin only.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/offenders", tags=["offenders"])


def _calculate_offender_score(persons: List[models.Person], all_persons_in_db: List[models.Person]) -> Tuple[int, str, schemas.OffenderRiskBreakdown]:
    """
    Given a cluster of Person records representing the same individual across cases,
    calculate their non-biased behavioral risk score (0-100).
    """
    # 1. Case Volume (10 pts per case, max 40)
    case_count = len(persons)
    volume_pts = min(40, case_count * 10)

    # 2. Severity (max 30)
    severity_map = {models.Severity.critical: 30, models.Severity.high: 20, models.Severity.medium: 10, models.Severity.low: 5}
    max_sev_pts = 0
    for p in persons:
        if p.case:
            sev_pts = severity_map.get(p.case.severity, 5)
            if sev_pts > max_sev_pts:
                max_sev_pts = sev_pts
    severity_pts = max_sev_pts

    # 3. Recency (max 25)
    now = datetime.utcnow()
    recency_pts = 0
    most_recent_date = None
    for p in persons:
        inc_date = p.case.incident_date if p.case else p.last_recorded_date
        if inc_date:
            if most_recent_date is None or inc_date > most_recent_date:
                most_recent_date = inc_date

    if most_recent_date:
        days_ago = (now - most_recent_date).days
        if days_ago <= 30:
            recency_pts = 25
        elif days_ago <= 90:
            recency_pts = 15
        elif days_ago <= 180:
            recency_pts = 5

    # 4. MO Repetition (max 30)
    mo_tags_collected = []
    for p in persons:
        if p.mo_tags:
            tags = [t.strip().lower() for t in p.mo_tags.split(",") if t.strip()]
            mo_tags_collected.extend(tags)
    
    unique_tags = set(mo_tags_collected)
    repeated_tags_count = len(mo_tags_collected) - len(unique_tags)
    mo_repetition_pts = min(30, max(0, repeated_tags_count * 15))

    # 5. Network Centrality (max 20)
    # Check phone links across distinct cases
    phones = {p.phone_number for p in persons if p.phone_number}
    network_centrality_pts = 0
    if phones:
        # Find how many other distinct persons in DB share these phone numbers
        matching_other_persons = [
            op for op in all_persons_in_db
            if op.phone_number in phones and op.case_id not in {p.case_id for p in persons}
        ]
        network_centrality_pts = min(20, len(matching_other_persons) * 10)

    total_score = min(100, volume_pts + severity_pts + recency_pts + mo_repetition_pts + network_centrality_pts)

    if total_score >= 70:
        category = "high"
    elif total_score >= 40:
        category = "medium"
    else:
        category = "low"

    breakdown = schemas.OffenderRiskBreakdown(
        volume_pts=volume_pts,
        severity_pts=severity_pts,
        recency_pts=recency_pts,
        mo_repetition_pts=mo_repetition_pts,
        network_centrality_pts=network_centrality_pts,
    )

    return total_score, category, breakdown


def _group_offenders(db: Session) -> Dict[str, List[models.Person]]:
    """Group person records by phone number or name to aggregate multi-case suspects."""
    all_persons = db.query(models.Person).options(joinedload(models.Person.case)).all()
    clusters: Dict[str, List[models.Person]] = {}

    for p in all_persons:
        # Key by phone number if present, else by lowercased name
        key = f"phone:{p.phone_number}" if p.phone_number else f"name:{p.name.strip().lower()}"
        clusters.setdefault(key, []).append(p)

    return clusters, all_persons


@router.get("", response_model=List[schemas.OffenderSummaryOut])
def list_offenders(
    min_risk: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "analyst", "admin")),
):
    clusters, all_persons = _group_offenders(db)
    results = []

    for key, p_group in clusters.items():
        # A cluster qualifies if: 2+ linked cases OR flagged offender OR role is suspect in 1+ case
        suspect_cases = [p for p in p_group if (p.role_in_case or "").lower() == "suspect" or p.is_flagged_offender]
        if len(p_group) >= 2 or len(suspect_cases) >= 1:
            primary = p_group[0]
            total_score, category, breakdown = _calculate_offender_score(p_group, all_persons)

            if min_risk and category != min_risk.lower():
                continue

            mo_tags = set()
            last_date = None
            for p in p_group:
                if p.mo_tags:
                    for t in p.mo_tags.split(","):
                        if t.strip():
                            mo_tags.add(t.strip())
                inc_date = p.case.incident_date if p.case else p.last_recorded_date
                if inc_date and (last_date is None or inc_date > last_date):
                    last_date = inc_date

            results.append(
                schemas.OffenderSummaryOut(
                    person_id=primary.id,
                    name=primary.name,
                    phone_number=primary.phone_number,
                    case_count=len(p_group),
                    mo_tags=sorted(list(mo_tags)),
                    last_recorded_date=last_date,
                    risk_score=total_score,
                    risk_category=category,
                    risk_breakdown=breakdown,
                )
            )

    results.sort(key=lambda x: x.risk_score, reverse=True)
    return results


@router.get("/{person_id}", response_model=schemas.OffenderDetailOut)
def get_offender_profile(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "analyst", "admin")),
):
    person = db.query(models.Person).filter(models.Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person record not found")

    clusters, all_persons = _group_offenders(db)
    key = f"phone:{person.phone_number}" if person.phone_number else f"name:{person.name.strip().lower()}"
    p_group = clusters.get(key, [person])

    total_score, category, breakdown = _calculate_offender_score(p_group, all_persons)

    linked_cases = [schemas.CaseOut.model_validate(p.case) for p in p_group if p.case]
    mo_tags = set()
    first_date, last_date = None, None

    for p in p_group:
        if p.mo_tags:
            for t in p.mo_tags.split(","):
                if t.strip():
                    mo_tags.add(t.strip())
        inc_date = p.case.incident_date if p.case else p.last_recorded_date
        if inc_date:
            if first_date is None or inc_date < first_date:
                first_date = inc_date
            if last_date is None or inc_date > last_date:
                last_date = inc_date

    # Network connections count
    phones = {p.phone_number for p in p_group if p.phone_number}
    network_connections_count = len([
        op for op in all_persons
        if op.phone_number in phones and op.case_id not in {p.case_id for p in p_group}
    ]) if phones else 0

    # Audit log
    log = models.AuditLog(
        user_id=current_user.id,
        action="view_offender_profile",
        detail=f"Viewed profile for offender {person.name} (Risk Score: {total_score})",
    )
    db.add(log)
    db.commit()

    return schemas.OffenderDetailOut(
        person_id=person.id,
        name=person.name,
        phone_number=person.phone_number,
        case_count=len(linked_cases),
        mo_tags=sorted(list(mo_tags)),
        first_recorded_date=first_date,
        last_recorded_date=last_date,
        risk_score=total_score,
        risk_category=category,
        risk_breakdown=breakdown,
        is_flagged_offender=any(p.is_flagged_offender for p in p_group),
        linked_cases=linked_cases,
        network_connections_count=network_connections_count,
    )
