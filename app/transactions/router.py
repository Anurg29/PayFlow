"""
/transactions  — Create, Get, List, Refund
"""

import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..auth.router import get_current_user
from ..cache import get_cached_transaction, set_cached_transaction, invalidate_transaction
from .service import check_anomalies

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _txn_to_dict(txn: models.Transaction) -> dict:
    return {
        "id": txn.id,
        "amount": txn.amount,
        "payment_method": txn.payment_method,
        "status": txn.status,
        "idempotency_key": txn.idempotency_key,
        "is_flagged": txn.is_flagged,
        "user_id": txn.user_id,
        "created_at": txn.created_at.isoformat(),
    }


# ── POST /transactions/ ── Create new payment ─────────────────────────────────
@router.post("/", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Idempotency check
    existing = (
        db.query(models.Transaction)
        .filter(models.Transaction.idempotency_key == payload.idempotency_key)
        .first()
    )
    if existing:
        return existing  # return existing result instead of charging again

    # Validate payment method
    valid_methods = {"upi", "card", "netbanking"}
    if payload.payment_method.lower() not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment_method. Choose from: {valid_methods}",
        )

    # Anomaly detection
    is_flagged = check_anomalies(db, current_user.id, payload.amount)

    # Create transaction (starts PENDING → PROCESSING → SUCCESS/FAILED)
    txn = models.Transaction(
        amount=payload.amount,
        payment_method=payload.payment_method.lower(),
        idempotency_key=payload.idempotency_key,
        status=models.TransactionStatus.PROCESSING,
        is_flagged=is_flagged,
        user_id=current_user.id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    # Simulate payment outcome (95 % success, 5 % fail)
    outcome = (
        models.TransactionStatus.SUCCESS
        if random.random() < 0.95
        else models.TransactionStatus.FAILED
    )
    txn.status = outcome
    db.commit()
    db.refresh(txn)

    # Cache it
    set_cached_transaction(txn.id, _txn_to_dict(txn))

    return txn


# ── GET /transactions/ ── List my transactions ────────────────────────────────
@router.get("/", response_model=List[schemas.TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == current_user.id)
        .order_by(models.Transaction.created_at.desc())
        .all()
    )


# ── GET /transactions/{id} ── Get transaction by ID ───────────────────────────
@router.get("/{txn_id}", response_model=schemas.TransactionOut)
def get_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Try cache first
    cached = get_cached_transaction(txn_id)
    if cached and cached["user_id"] == current_user.id:
        return cached

    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    set_cached_transaction(txn.id, _txn_to_dict(txn))
    return txn


# ── POST /transactions/{id}/refund ── Refund ──────────────────────────────────
@router.post("/{txn_id}/refund", response_model=schemas.TransactionOut)
def refund_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    if txn.status != models.TransactionStatus.SUCCESS:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund a transaction with status '{txn.status}'",
        )

    txn.status = models.TransactionStatus.REFUNDED
    db.commit()
    db.refresh(txn)

    # Invalidate cache
    invalidate_transaction(txn_id)

    return txn
