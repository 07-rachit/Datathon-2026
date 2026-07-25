"""
Financial Crime & Transaction Link Analysis Router.

Enables tracking of illicit monetary trails linked to cases and accused persons.
Access: investigator, analyst, admin only.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.post("/accounts", response_model=schemas.FinancialAccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: schemas.FinancialAccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    account = models.FinancialAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=List[schemas.FinancialAccountOut])
def list_accounts(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "analyst", "admin")),
):
    query = db.query(models.FinancialAccount)
    if person_id:
        query = query.filter(models.FinancialAccount.person_id == person_id)
    return query.all()


@router.post("/transactions", response_model=schemas.FinancialTransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: schemas.FinancialTransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "admin")),
):
    tx = models.FinancialTransaction(**payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/transactions", response_model=List[schemas.FinancialTransactionOut])
def list_transactions(
    case_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "analyst", "admin")),
):
    query = db.query(models.FinancialTransaction).options(
        joinedload(models.FinancialTransaction.from_account),
        joinedload(models.FinancialTransaction.to_account),
    )
    if case_id:
        query = query.filter(models.FinancialTransaction.case_id == case_id)

    txs = query.order_by(models.FinancialTransaction.transaction_date.desc()).all()
    results = []
    for t in txs:
        item = schemas.FinancialTransactionOut.model_validate(t)
        item.from_account_masked = t.from_account.account_number_masked if t.from_account else None
        item.to_account_masked = t.to_account.account_number_masked if t.to_account else None
        results.append(item)
    return results


@router.get("/trail/{case_id}", response_model=schemas.FinancialTrailOut)
def get_financial_trail(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "analyst", "admin")),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Fetch all transactions linked directly to this case
    transactions = (
        db.query(models.FinancialTransaction)
        .options(
            joinedload(models.FinancialTransaction.from_account).joinedload(models.FinancialAccount.person),
            joinedload(models.FinancialTransaction.to_account).joinedload(models.FinancialAccount.person),
        )
        .filter(models.FinancialTransaction.case_id == case_id)
        .all()
    )

    nodes_dict = {}
    edges = []
    total_amount = 0.0
    flagged_count = 0

    for tx in transactions:
        total_amount += tx.amount
        if tx.flagged_reason:
            flagged_count += 1

        # Add from_account node
        if tx.from_account and tx.from_account.id not in nodes_dict:
            nodes_dict[tx.from_account.id] = schemas.FinancialTrailNode(
                id=tx.from_account.id,
                bank_name=tx.from_account.bank_name,
                account_number_masked=tx.from_account.account_number_masked,
                account_type=tx.from_account.account_type,
                person_name=tx.from_account.person.name if tx.from_account.person else None,
            )

        # Add to_account node
        if tx.to_account and tx.to_account.id not in nodes_dict:
            nodes_dict[tx.to_account.id] = schemas.FinancialTrailNode(
                id=tx.to_account.id,
                bank_name=tx.to_account.bank_name,
                account_number_masked=tx.to_account.account_number_masked,
                account_type=tx.to_account.account_type,
                person_name=tx.to_account.person.name if tx.to_account.person else None,
            )

        edges.append(
            schemas.FinancialTrailEdge(
                id=tx.id,
                source=tx.from_account_id,
                target=tx.to_account_id,
                amount=tx.amount,
                date=tx.transaction_date,
                flagged_reason=tx.flagged_reason,
            )
        )

    # Audit log
    log = models.AuditLog(
        user_id=current_user.id,
        action="view_financial_trail",
        detail=f"Viewed financial transaction trail for case {case.case_id} ({len(edges)} transactions)",
    )
    db.add(log)
    db.commit()

    return schemas.FinancialTrailOut(
        case_id=case.id,
        total_amount=round(total_amount, 2),
        flagged_count=flagged_count,
        nodes=list(nodes_dict.values()),
        edges=edges,
    )
