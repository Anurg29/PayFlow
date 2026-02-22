"""
/admin  — All txns, Flagged txns, Stats
Only accessible by users with role = "admin".
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..auth.router import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ── GET /admin/transactions ── All transactions ───────────────────────────────
@router.get("/transactions", response_model=List[schemas.TransactionOut])
def all_transactions(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return (
        db.query(models.Transaction)
        .order_by(models.Transaction.created_at.desc())
        .all()
    )


# ── GET /admin/flagged ── Flagged / anomalous transactions ─────────────────────
@router.get("/flagged", response_model=List[schemas.TransactionOut])
def flagged_transactions(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.is_flagged == True)
        .order_by(models.Transaction.created_at.desc())
        .all()
    )


# ── GET /admin/stats ── System-wide stats ─────────────────────────────────────
@router.get("/stats", response_model=schemas.TransactionStats)
def transaction_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    all_txns = db.query(models.Transaction).all()

    total_amount = sum(t.amount for t in all_txns)
    success_count = sum(1 for t in all_txns if t.status == models.TransactionStatus.SUCCESS)
    failed_count = sum(1 for t in all_txns if t.status == models.TransactionStatus.FAILED)
    flagged_count = sum(1 for t in all_txns if t.is_flagged)

    return schemas.TransactionStats(
        total_transactions=len(all_txns),
        total_amount=total_amount,
        success_count=success_count,
        failed_count=failed_count,
        flagged_count=flagged_count,
    )
