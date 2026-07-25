"""
Sociological / Socio-demographic Crime Insights Router.

Provides AGGREGATE statistical distributions, district-level socioeconomic
correlations, and seasonal/event-based crime trend patterns for policy, resourcing, and preventive strategy.

SAFETY GUARANTEE: Individual-level demographic attributes are NEVER exposed or
used for targeting. All endpoints return anonymized aggregate counts.
"""
import calendar
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas, auth
from app.websocket import broadcast_notification_to_roles

router = APIRouter(prefix="/api/analytics", tags=["analytics"])



@router.get("/demographics", response_model=schemas.DemographicsSummaryOut)
def get_demographic_insights(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("analyst", "admin")),
):
    persons = db.query(models.Person).all()

    # 1. Age group breakdown
    age_groups = {"18-25": 0, "26-35": 0, "36-50": 0, "50+": 0, "Unknown": 0}
    for p in persons:
        if p.age is None:
            age_groups["Unknown"] += 1
        elif p.age <= 25:
            age_groups["18-25"] += 1
        elif p.age <= 35:
            age_groups["26-35"] += 1
        elif p.age <= 50:
            age_groups["36-50"] += 1
        else:
            age_groups["50+"] += 1

    by_age_group = [schemas.GroupCount(label=k, count=v) for k, v in age_groups.items() if v > 0]

    # 2. Gender distribution
    gender_counts = {}
    for p in persons:
        g = (p.gender or "unspecified").capitalize()
        gender_counts[g] = gender_counts.get(g, 0) + 1
    by_gender = [schemas.GroupCount(label=k, count=v) for k, v in gender_counts.items()]

    # 3. Area type
    area_counts = {}
    for p in persons:
        a = (p.area_type or "unspecified").capitalize()
        area_counts[a] = area_counts.get(a, 0) + 1
    by_area_type = [schemas.GroupCount(label=k, count=v) for k, v in area_counts.items()]

    # 4. Education level
    edu_counts = {}
    for p in persons:
        e = (p.education_level or "unspecified").capitalize()
        edu_counts[e] = edu_counts.get(e, 0) + 1
    by_education = [schemas.GroupCount(label=k, count=v) for k, v in edu_counts.items()]

    return schemas.DemographicsSummaryOut(
        by_age_group=by_age_group,
        by_gender=by_gender,
        by_area_type=by_area_type,
        by_education=by_education,
    )


@router.get("/socioeconomic-correlation", response_model=schemas.SocioeconomicCorrelationOut)
def get_socioeconomic_correlation(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("analyst", "admin")),
):
    # Query case count per district
    case_counts = dict(
        db.query(models.Case.district, func.count(models.Case.id))
        .group_by(models.Case.district)
        .all()
    )

    indicators = db.query(models.DistrictIndicator).all()
    results: List[schemas.DistrictCorrelationItem] = []

    for ind in indicators:
        results.append(
            schemas.DistrictCorrelationItem(
                district=ind.district,
                crime_count=case_counts.get(ind.district, 0),
                unemployment_rate=ind.unemployment_rate,
                literacy_rate=ind.literacy_rate,
                urbanization_pct=ind.urbanization_pct,
                population=ind.population,
            )
        )

    # Sort by crime count descending
    results.sort(key=lambda x: x.crime_count, reverse=True)

    return schemas.SocioeconomicCorrelationOut(district_correlations=results)


@router.get("/seasonal-trends")
def get_seasonal_trends(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "analyst", "admin")),
):
    """
    Returns case volume aggregations by Month-of-Year and Day-of-Week
    plus high-context reference event windows (Festivals, Elections, Holidays).
    """
    cases = db.query(models.Case).all()

    month_counts = {m: 0 for m in range(1, 13)}
    weekday_counts = {w: 0 for w in range(7)}  # 0=Monday, 6=Sunday

    for c in cases:
        if c.incident_date:
            m = c.incident_date.month
            w = c.incident_date.weekday()
            month_counts[m] += 1
            weekday_counts[w] += 1

    month_data = [
        {"month": calendar.month_abbr[m], "month_num": m, "case_count": count}
        for m, count in month_counts.items()
    ]

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_data = [
        {"day": weekday_names[w], "day_num": w, "case_count": count}
        for w, count in weekday_counts.items()
    ]

    events = [
        {"name": "General Election Period", "period": "April – May", "risk_level": "High (Commercial & Cyber Fraud)"},
        {"name": "Festival & Harvest Season (Dasara / Diwali)", "period": "October – November", "risk_level": "High (Burglary & Theft)"},
        {"name": "Year-End & New Year Period", "period": "Late December", "risk_level": "Medium (Public Disorder & Assault)"},
    ]

    return {
        "monthly_trends": month_data,
        "weekday_trends": weekday_data,
        "high_context_events": events,
    }



@router.post("/trigger-trend-alert")
async def trigger_district_trend_alert(
    district: str,
    crime_type: str,
    spike_pct: float,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("analyst", "admin")),
):
    """Trigger a district predictive trend alert notification to supervisory roles."""
    await broadcast_notification_to_roles(
        db=db,
        roles=[models.RoleEnum.analyst, models.RoleEnum.admin],
        notification_type="district_trend_alert",
        title=f"📈 Predictive Alert: {district}",
        message=f"{spike_pct:.0f}% spike in {crime_type} incidents detected in {district} over past 30 days.",
    )
    return {"status": "ok", "message": f"Trend alert dispatched for {district}"}

