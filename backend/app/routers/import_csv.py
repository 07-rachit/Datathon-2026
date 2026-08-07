"""
Bulk case import via CSV upload using standard library csv module.
Zero heavy dependencies.
"""
import csv
import io
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth, rag

router = APIRouter(prefix="/api/import", tags=["import"])

REQUIRED_COLS = {
    "case_id", "title", "crime_type", "district", "station_name",
    "status", "severity", "incident_date",
}


@router.post("/cases", status_code=status.HTTP_200_OK)
@router.post("/cases/csv", status_code=status.HTTP_200_OK)
def import_cases_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("analyst", "admin")),
):
    """
    Import case records from CSV file.
    Expected headers: case_id, title, crime_type, district, station_name,
                      status, severity, incident_date, lat, lng, summary, modus_operandi
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = file.file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])

    missing = REQUIRED_COLS - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required CSV columns: {', '.join(sorted(missing))}"
        )

    imported_count = 0
    updated_count = 0
    errors = []

    for idx, row in enumerate(reader, start=2):
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            errors.append(f"Line {idx}: Empty case_id")
            continue

        try:
            inc_date = None
            date_str = (row.get("incident_date") or "").strip()
            if date_str:
                for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        inc_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        pass
                if not inc_date:
                    inc_date = datetime.utcnow()
            else:
                inc_date = datetime.utcnow()

            lat = float(row["lat"]) if row.get("lat") else 25.5941
            lng = float(row["lng"]) if row.get("lng") else 85.1376

            existing = db.query(models.Case).filter(models.Case.case_id == case_id).first()
            raw_status = (row.get("status") or "open").lower().strip()
            raw_severity = (row.get("severity") or "medium").lower().strip()

            if existing:
                existing.title = (row.get("title") or existing.title).strip()
                existing.crime_type = (row.get("crime_type") or existing.crime_type).strip()
                existing.district = (row.get("district") or existing.district).strip()
                existing.station_name = (row.get("station_name") or existing.station_name).strip()
                existing.status = raw_status
                existing.severity = raw_severity
                existing.incident_date = inc_date
                existing.latitude = lat
                existing.longitude = lng
                existing.summary = (row.get("summary") or existing.summary).strip()
                updated_count += 1
            else:
                new_case = models.Case(
                    case_id=case_id,
                    title=(row.get("title") or "").strip(),
                    crime_type=(row.get("crime_type") or "General").strip(),
                    district=(row.get("district") or "Bengaluru").strip(),
                    station_name=(row.get("station_name") or "Central PS").strip(),
                    status=raw_status,
                    severity=raw_severity,
                    incident_date=inc_date,
                    latitude=lat,
                    longitude=lng,
                    summary=(row.get("summary") or "").strip(),
                )
                db.add(new_case)
                imported_count += 1
        except Exception as e:
            errors.append(f"Line {idx} ({case_id}): {str(e)}")

    db.commit()

    try:
        rag.build_index(db)
    except Exception as e:
        print(f"RAG reindex warning: {e}")

    return {
        "status": "success",
        "imported": imported_count,
        "updated": updated_count,
        "skipped": [{"row": err.split(":")[0], "reason": err} for err in errors],
        "total_processed": imported_count + updated_count,
    }


@router.get("/template")
@router.get("/cases/csv/template")
def download_csv_template(
    current_user: models.User = Depends(auth.get_current_user),
):
    """Generates a sample CSV template for bulk case uploads."""
    template_data = (
        "case_id,title,crime_type,district,station_name,status,severity,incident_date,lat,lng,summary\n"
        "CR-2026-9901,Bank Fraud Scam,Cybercrime,Bengaluru,Cyber Crime PS,open,high,2026-03-15,12.9716,77.5946,Phishing call targeted senior citizen\n"
        "CR-2026-9902,Highway Robbery,Robbery,Mysuru,Civil Lines PS,under_review,critical,2026-03-18,12.2958,76.6394,Armed hijack of freight container\n"
    )
    from fastapi.responses import Response
    return Response(
        content=template_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="crime_cases_template.csv"'}
    )
