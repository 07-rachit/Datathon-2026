from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/predictions")
def get_predictions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """
    Lightweight trend signal: compare incident counts in the last 30 days against
    the prior 30 days, per district. Districts trending up are surfaced as
    predictive alerts worth an analyst's attention. This is a simple heuristic,
    not a statistical model - swap in a proper time-series model later.
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    recent_start = now - timedelta(days=30)
    prior_start = now - timedelta(days=60)

    all_cases = db.query(models.Case).filter(models.Case.incident_date >= prior_start).all()

    recent_counts: dict = {}
    prior_counts: dict = {}
    for case in all_cases:
        bucket = recent_counts if case.incident_date >= recent_start else prior_counts
        bucket[case.district] = bucket.get(case.district, 0) + 1

    districts = set(recent_counts) | set(prior_counts)
    alerts = []
    for district in districts:
        recent = recent_counts.get(district, 0)
        prior = prior_counts.get(district, 0)
        if prior == 0 and recent == 0:
            continue
        change_pct = ((recent - prior) / prior * 100) if prior > 0 else 100.0
        alerts.append({
            "district": district,
            "recent_30d": recent,
            "prior_30d": prior,
            "change_pct": round(change_pct, 1),
            "trend": "rising" if change_pct > 15 else ("falling" if change_pct < -15 else "stable"),
        })

    alerts.sort(key=lambda a: a["change_pct"], reverse=True)
    return {"alerts": alerts}


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    total_cases = db.query(models.Case).count()
    open_cases = db.query(models.Case).filter(models.Case.status == models.CaseStatus.open).count()
    closed_cases = db.query(models.Case).filter(models.Case.status == models.CaseStatus.closed).count()
    under_review_cases = db.query(models.Case).filter(models.Case.status == models.CaseStatus.under_review).count()

    crime_type_rows = (
        db.query(models.Case.crime_type, func.count(models.Case.id))
        .group_by(models.Case.crime_type)
        .order_by(func.count(models.Case.id).desc())
        .all()
    )
    district_rows = (
        db.query(models.Case.district, func.count(models.Case.id))
        .group_by(models.Case.district)
        .order_by(func.count(models.Case.id).desc())
        .all()
    )

    recent_alerts = (
        db.query(models.Case)
        .filter(models.Case.severity.in_([models.Severity.high, models.Severity.critical]))
        .order_by(models.Case.incident_date.desc())
        .limit(5)
        .all()
    )

    return schemas.DashboardStats(
        total_cases=total_cases,
        open_cases=open_cases,
        closed_cases=closed_cases,
        under_review_cases=under_review_cases,
        crime_type_distribution=[
            schemas.CrimeTypeCount(crime_type=ct, count=c) for ct, c in crime_type_rows
        ],
        district_summary=[
            schemas.DistrictCount(district=d, count=c) for d, c in district_rows
        ],
        recent_alerts=recent_alerts,
    )
