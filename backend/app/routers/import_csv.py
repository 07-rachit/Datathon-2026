"""
Bulk case import via CSV upload.

Expected CSV columns (case-insensitive headers):
  case_id, title, crime_type, district, station_name,
  status, severity, incident_date, latitude, longitude, summary

incident_date must be parseable by pandas (ISO format recommended: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
Rows with duplicate case_id (already in DB) are skipped and reported.
Rows that fail validation are skipped and reported with the reason.

Access: admin + investigator roles only.
"""
import io
from datetime import datetime
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth, rag

router = APIRouter(prefix="/api/import", tags=["import"])

REQUIRED_COLS = {
    "case_id", "title", "crime_type", "district", "station_name",
    "status", "severity", "incident_date",
}

VALID_STATUSES = {s.value for s in models.CaseStatus}
VALID_SEVERITIES = {s.value for s in models.Severity}


def _parse_df(content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {', '.join(sorted(missing))}",
        )
    return df


@router.post("/cases/csv", response_model=schemas.ImportResult)
def import_cases_csv(
    file: UploadFile = File(..., description="CSV file with case records"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "investigator")),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = file.file.read()
    if len(content) > 5 * 1024 * 1024:  # 5 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    df = _parse_df(content)

    imported = 0
    skipped: List[schemas.ImportSkippedRow] = []

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-indexed, +1 for header

        raw_case_id = str(row.get("case_id", "")).strip()
        if not raw_case_id:
            skipped.append(schemas.ImportSkippedRow(row=row_num, reason="case_id is empty"))
            continue

        # Duplicate check
        if db.query(models.Case).filter(models.Case.case_id == raw_case_id).first():
            skipped.append(schemas.ImportSkippedRow(row=row_num, reason=f"case_id '{raw_case_id}' already exists"))
            continue

        # Validate status / severity
        raw_status = str(row.get("status", "open")).strip().lower()
        raw_severity = str(row.get("severity", "medium")).strip().lower()
        if raw_status not in VALID_STATUSES:
            skipped.append(schemas.ImportSkippedRow(row=row_num, reason=f"invalid status '{raw_status}'"))
            continue
        if raw_severity not in VALID_SEVERITIES:
            skipped.append(schemas.ImportSkippedRow(row=row_num, reason=f"invalid severity '{raw_severity}'"))
            continue

        # Parse date
        raw_date = row.get("incident_date", "")
        try:
            incident_date = pd.to_datetime(raw_date).to_pydatetime()
        except Exception:
            skipped.append(schemas.ImportSkippedRow(row=row_num, reason=f"cannot parse incident_date '{raw_date}'"))
            continue

        # Optional geo fields
        def _float_or_none(val):
            try:
                return float(val) if pd.notna(val) and str(val).strip() != "" else None
            except (ValueError, TypeError):
                return None

        try:
            case = models.Case(
                case_id=raw_case_id,
                title=str(row.get("title", "")).strip()[:300] or "(no title)",
                crime_type=str(row.get("crime_type", "")).strip()[:120] or "Unknown",
                district=str(row.get("district", "")).strip()[:120] or "Unknown",
                station_name=str(row.get("station_name", "")).strip()[:120] or "Unknown",
                status=models.CaseStatus(raw_status),
                severity=models.Severity(raw_severity),
                incident_date=incident_date,
                latitude=_float_or_none(row.get("latitude")),
                longitude=_float_or_none(row.get("longitude")),
                summary=str(row.get("summary", "")).strip()[:5000] or None,
            )
            db.add(case)
            imported += 1
        except Exception as exc:
            skipped.append(schemas.ImportSkippedRow(row=row_num, reason=str(exc)))
            continue

    db.commit()

    log = models.AuditLog(
        user_id=current_user.id,
        action="import_cases_csv",
        detail=f"Imported {imported} cases; skipped {len(skipped)} rows from {file.filename}",
    )
    db.add(log)
    db.commit()

    # Rebuild RAG index with new cases
    if imported > 0:
        rag.build_index(db)

    return schemas.ImportResult(imported=imported, skipped=skipped)


@router.get("/cases/csv/template")
def download_csv_template():
    """Return a CSV template file with the required column headers."""
    from fastapi.responses import Response

    header = "case_id,title,crime_type,district,station_name,status,severity,incident_date,latitude,longitude,summary\n"
    example = 'CR-2026-9001,"Theft at Market St","Theft","Central District","PS Central","open","medium","2026-07-01",28.6139,77.2090,"Brief description of the incident."\n'
    content = header + example
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=case_import_template.csv"},
    )
