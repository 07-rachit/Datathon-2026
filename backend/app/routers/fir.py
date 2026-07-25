"""
FIR Details & KSP Compatibility Router.

Manages FIR structured metadata, Complainant details (with statutory sensitive data masking),
Arrest/Surrender events, Act/Sections, and Chargesheet records.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/cases", tags=["fir"])


# ── 1. FIR Core Details ──────────────────────────────────────────────────────

@router.post("/{case_id}/fir-details", response_model=schemas.CaseFIRDetailsOut, status_code=status.HTTP_201_CREATED)
def create_or_update_fir_details(
    case_id: str,
    payload: schemas.CaseFIRDetailsCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    existing = db.query(models.CaseFIRDetails).filter(models.CaseFIRDetails.case_id == case_id).first()
    
    crime_no = payload.crime_no
    if not crime_no:
        if existing:
            crime_no = existing.crime_no
        else:
            # Auto-generate 18-digit structured crime number
            serial_count = db.query(models.CaseFIRDetails).count() + 1
            crime_no = schemas.generate_crime_no(serial=serial_count)

    data = payload.model_dump(exclude_unset=True)
    data["crime_no"] = crime_no
    data["case_id"] = case_id

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        fir_obj = existing
    else:
        fir_obj = models.CaseFIRDetails(**data)
        db.add(fir_obj)

    db.commit()
    db.refresh(fir_obj)

    return _build_fir_out(fir_obj)


@router.get("/{case_id}/fir-details", response_model=Optional[schemas.CaseFIRDetailsOut])
def get_fir_details(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    fir_obj = (
        db.query(models.CaseFIRDetails)
        .options(
            joinedload(models.CaseFIRDetails.category),
            joinedload(models.CaseFIRDetails.gravity),
            joinedload(models.CaseFIRDetails.crime_head),
            joinedload(models.CaseFIRDetails.crime_sub_head),
            joinedload(models.CaseFIRDetails.status_master),
            joinedload(models.CaseFIRDetails.court),
            joinedload(models.CaseFIRDetails.police_station),
            joinedload(models.CaseFIRDetails.registering_officer),
        )
        .filter(models.CaseFIRDetails.case_id == case_id)
        .first()
    )
    if not fir_obj:
        return None
    return _build_fir_out(fir_obj)


def _build_fir_out(f: models.CaseFIRDetails) -> schemas.CaseFIRDetailsOut:
    return schemas.CaseFIRDetailsOut(
        id=f.id,
        case_id=f.case_id,
        crime_no=f.crime_no,
        case_no=f.case_no,
        crime_registered_date=f.crime_registered_date,
        incident_from_date=f.incident_from_date,
        incident_to_date=f.incident_to_date,
        info_received_ps_date=f.info_received_ps_date,
        category_name=f.category.name if f.category else None,
        gravity_name=f.gravity.name if f.gravity else None,
        crime_head_name=f.crime_head.name if f.crime_head else None,
        crime_sub_head_name=f.crime_sub_head.name if f.crime_sub_head else None,
        case_status_name=f.status_master.name if f.status_master else None,
        court_name=f.court.court_name if f.court else None,
        police_station_name=f.police_station.unit_name if f.police_station else None,
        registering_officer_name=f.registering_officer.name if f.registering_officer else None,
    )


# ── 2. Complainant Details (Sensitive Field Masking Protocol) ────────────────

@router.post("/{case_id}/complainant", response_model=schemas.ComplainantDetailsOut, status_code=status.HTTP_201_CREATED)
def create_or_update_complainant(
    case_id: str,
    payload: schemas.ComplainantDetailsCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    existing = db.query(models.ComplainantDetails).filter(models.ComplainantDetails.case_id == case_id).first()
    data = payload.model_dump(exclude_unset=True)
    data["case_id"] = case_id

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        comp_obj = existing
    else:
        comp_obj = models.ComplainantDetails(**data)
        db.add(comp_obj)

    db.commit()
    db.refresh(comp_obj)

    return _build_complainant_out(comp_obj, current_user, db)


@router.get("/{case_id}/complainant", response_model=Optional[schemas.ComplainantDetailsOut])
def get_complainant_details(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    comp_obj = (
        db.query(models.ComplainantDetails)
        .options(
            joinedload(models.ComplainantDetails.occupation),
            joinedload(models.ComplainantDetails.religion),
            joinedload(models.ComplainantDetails.caste),
        )
        .filter(models.ComplainantDetails.case_id == case_id)
        .first()
    )
    if not comp_obj:
        return None

    # Log audit event if admin reads sensitive complainant data
    if current_user.role == models.RoleEnum.admin and (comp_obj.religion_id or comp_obj.caste_id):
        log = models.AuditLog(
            user_id=current_user.id,
            action="view_sensitive_complainant_data",
            detail=f"Admin accessed statutory-restricted religion/caste fields for complainant on case {case_id}",
        )
        db.add(log)
        db.commit()

    return _build_complainant_out(comp_obj, current_user, db)


def _build_complainant_out(c: models.ComplainantDetails, user: models.User, db: Session) -> schemas.ComplainantDetailsOut:
    # Sensitive masking: Return religion and caste ONLY to admin role
    is_admin = user.role == models.RoleEnum.admin

    rel_name = c.religion.name if (is_admin and c.religion) else None
    caste_name = c.caste.name if (is_admin and c.caste) else None

    return schemas.ComplainantDetailsOut(
        id=c.id,
        case_id=c.case_id,
        name=c.name,
        age=c.age,
        gender=c.gender,
        occupation_name=c.occupation.name if c.occupation else None,
        religion_name=rel_name,
        caste_name=caste_name,
    )


# ── 3. Arrest / Surrender Events ─────────────────────────────────────────────

@router.post("/{case_id}/arrest-surrender", response_model=schemas.ArrestSurrenderOut, status_code=status.HTTP_201_CREATED)
def create_arrest_surrender(
    case_id: str,
    payload: schemas.ArrestSurrenderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    event = models.ArrestSurrender(**payload.model_dump(), case_id=case_id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return _build_arrest_out(event)


@router.get("/{case_id}/arrest-surrender", response_model=List[schemas.ArrestSurrenderOut])
def list_arrest_surrender(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    events = (
        db.query(models.ArrestSurrender)
        .options(
            joinedload(models.ArrestSurrender.accused_person),
            joinedload(models.ArrestSurrender.unit),
            joinedload(models.ArrestSurrender.investigating_officer),
            joinedload(models.ArrestSurrender.court),
        )
        .filter(models.ArrestSurrender.case_id == case_id)
        .all()
    )
    return [_build_arrest_out(e) for e in events]


def _build_arrest_out(e: models.ArrestSurrender) -> schemas.ArrestSurrenderOut:
    return schemas.ArrestSurrenderOut(
        id=e.id,
        case_id=e.case_id,
        accused_person_id=e.accused_person_id,
        accused_name=e.accused_person.name if e.accused_person else None,
        event_type=e.event_type,
        event_date=e.event_date,
        unit_name=e.unit.unit_name if e.unit else None,
        officer_name=e.investigating_officer.name if e.investigating_officer else None,
        court_name=e.court.court_name if e.court else None,
        is_accused=e.is_accused,
        is_complainant_accused=e.is_complainant_accused,
    )


# ── 4. Act & Section Associations ───────────────────────────────────────────

@router.post("/{case_id}/act-sections", response_model=schemas.ActSectionAssociationOut, status_code=status.HTTP_201_CREATED)
def add_act_section(
    case_id: str,
    payload: schemas.ActSectionAssociationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    assoc = models.ActSectionAssociation(**payload.model_dump(), case_id=case_id)
    db.add(assoc)
    db.commit()
    db.refresh(assoc)
    return _build_act_section_out(assoc)


@router.get("/{case_id}/act-sections", response_model=List[schemas.ActSectionAssociationOut])
def list_act_sections(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    assocs = (
        db.query(models.ActSectionAssociation)
        .options(
            joinedload(models.ActSectionAssociation.act),
            joinedload(models.ActSectionAssociation.section),
        )
        .filter(models.ActSectionAssociation.case_id == case_id)
        .order_by(models.ActSectionAssociation.display_order.asc())
        .all()
    )
    return [_build_act_section_out(a) for a in assocs]


def _build_act_section_out(a: models.ActSectionAssociation) -> schemas.ActSectionAssociationOut:
    return schemas.ActSectionAssociationOut(
        id=a.id,
        case_id=a.case_id,
        act_id=a.act_id,
        section_id=a.section_id,
        act_name=a.act.name if a.act else None,
        section_number=a.section.section_number if a.section else None,
        section_description=a.section.description if a.section else None,
        display_order=a.display_order,
    )


# ── 5. Chargesheet Details ───────────────────────────────────────────────────

@router.post("/{case_id}/chargesheet", response_model=schemas.ChargesheetDetailsOut, status_code=status.HTTP_201_CREATED)
def create_or_update_chargesheet(
    case_id: str,
    payload: schemas.ChargesheetDetailsCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    existing = db.query(models.ChargesheetDetails).filter(models.ChargesheetDetails.case_id == case_id).first()
    data = payload.model_dump(exclude_unset=True)
    data["case_id"] = case_id

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        cs_obj = existing
    else:
        cs_obj = models.ChargesheetDetails(**data)
        db.add(cs_obj)

    db.commit()
    db.refresh(cs_obj)
    return _build_cs_out(cs_obj)


@router.get("/{case_id}/chargesheet", response_model=Optional[schemas.ChargesheetDetailsOut])
def get_chargesheet(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    cs_obj = (
        db.query(models.ChargesheetDetails)
        .options(joinedload(models.ChargesheetDetails.filing_officer))
        .filter(models.ChargesheetDetails.case_id == case_id)
        .first()
    )
    if not cs_obj:
        return None
    return _build_cs_out(cs_obj)


def _build_cs_out(c: models.ChargesheetDetails) -> schemas.ChargesheetDetailsOut:
    return schemas.ChargesheetDetailsOut(
        id=c.id,
        case_id=c.case_id,
        chargesheet_date=c.chargesheet_date,
        cs_type=c.cs_type,
        filing_officer_name=c.filing_officer.name if c.filing_officer else None,
        remarks=c.remarks,
    )
