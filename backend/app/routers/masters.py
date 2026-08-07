"""
Read-only Reference Lookup Masters Router (KSP FIR Schema).

Exposes reference dropdown options for frontend case creation/edit forms.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/masters", tags=["masters"])


@router.get("/categories", response_model=List[schemas.MasterLookupOut])
def get_categories(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.CaseCategoryMaster).filter(models.CaseCategoryMaster.is_active == True).all()


@router.get("/gravity-offences", response_model=List[schemas.MasterLookupOut])
def get_gravity_offences(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.GravityOffenceMaster).filter(models.GravityOffenceMaster.is_active == True).all()


@router.get("/crime-heads", response_model=List[schemas.MasterLookupOut])
def get_crime_heads(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.CrimeHead).filter(models.CrimeHead.is_active == True).all()


@router.get("/crime-sub-heads", response_model=List[schemas.CrimeSubHeadOut])
def get_crime_sub_heads(
    head_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.CrimeSubHead).filter(models.CrimeSubHead.is_active == True)
    if head_id:
        query = query.filter(models.CrimeSubHead.crime_head_id == head_id)
    return query.all()


@router.get("/statuses", response_model=List[schemas.MasterLookupOut])
def get_statuses(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.CaseStatusMaster).filter(models.CaseStatusMaster.is_active == True).all()


@router.get("/acts", response_model=List[schemas.MasterLookupOut])
def get_acts(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Act).filter(models.Act.is_active == True).all()


@router.get("/sections", response_model=List[schemas.SectionOut])
def get_sections(
    act_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Section).filter(models.Section.is_active == True)
    if act_id:
        query = query.filter(models.Section.act_id == act_id)
    return query.all()


@router.get("/occupations", response_model=List[schemas.MasterLookupOut])
def get_occupations(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.OccupationMaster).filter(models.OccupationMaster.is_active == True).all()


@router.get("/religions", response_model=List[schemas.MasterLookupOut])
def get_religions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.ReligionMaster).filter(models.ReligionMaster.is_active == True).all()


@router.get("/castes", response_model=List[schemas.MasterLookupOut])
def get_castes(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.CasteMaster).filter(models.CasteMaster.is_active == True).all()


@router.get("/units", response_model=List[schemas.UnitMasterOut])
def get_units(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.UnitMaster).filter(models.UnitMaster.is_active == True).all()


@router.get("/courts", response_model=List[schemas.CourtMasterOut])
def get_courts(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.CourtMaster).filter(models.CourtMaster.is_active == True).all()


@router.get("/employees", response_model=List[schemas.EmployeeMasterOut])
def get_employees(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    employees = db.query(models.EmployeeMaster).options(
        joinedload(models.EmployeeMaster.rank),
        joinedload(models.EmployeeMaster.designation),
        joinedload(models.EmployeeMaster.unit),
    ).filter(models.EmployeeMaster.is_active == True).all()

    results = []
    for emp in employees:
        results.append(
            schemas.EmployeeMasterOut(
                id=emp.id,
                kgid=emp.kgid,
                name=emp.name,
                gender=emp.gender,
                rank_name=emp.rank.name if emp.rank else None,
                designation_name=emp.designation.name if emp.designation else None,
                unit_name=emp.unit.unit_name if emp.unit else None,
            )
        )
    return results
