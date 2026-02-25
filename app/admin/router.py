"""
/admin  — System-wide admin dashboard.
Only accessible by users with role = "admin".
Covers: legacy transactions + new gateway entities.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from .. import models, schemas
from ..auth.router import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY TRANSACTIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/transactions", response_model=List[schemas.TransactionOut], summary="All legacy transactions")
def all_transactions(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return (
        db.query(models.Transaction)
        .order_by(models.Transaction.created_at.desc())
        .all()
    )


@router.get("/flagged", response_model=List[schemas.TransactionOut], summary="Flagged transactions")
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


@router.get("/stats", response_model=schemas.TransactionStats, summary="Legacy transaction stats")
def transaction_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    all_txns = db.query(models.Transaction).all()
    return schemas.TransactionStats(
        total_transactions=len(all_txns),
        total_amount=sum(t.amount for t in all_txns),
        success_count=sum(1 for t in all_txns if t.status == models.TransactionStatus.SUCCESS),
        failed_count=sum(1 for t in all_txns if t.status == models.TransactionStatus.FAILED),
        flagged_count=sum(1 for t in all_txns if t.is_flagged),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/stats",
    response_model=schemas.GatewayStats,
    summary="Gateway-wide statistics",
    description="Total merchants, orders, payments, refunds and transaction volume across the whole platform.",
)
def gateway_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    total_merchants = db.query(func.count(models.Merchant.id)).scalar() or 0
    total_orders    = db.query(func.count(models.Order.id)).scalar() or 0
    total_payments  = db.query(func.count(models.Payment.id)).scalar() or 0
    total_volume    = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.status == models.PaymentStatus.CAPTURED
    ).scalar() or 0
    total_refunds   = db.query(func.count(models.Refund.id)).scalar() or 0

    return schemas.GatewayStats(
        total_merchants=total_merchants,
        total_orders=total_orders,
        total_payments=total_payments,
        total_volume_paise=total_volume,
        total_refunds=total_refunds,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — MERCHANTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/merchants",
    response_model=List[schemas.MerchantOut],
    summary="List all merchants",
)
def all_merchants(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return db.query(models.Merchant).order_by(models.Merchant.created_at.desc()).all()


@router.patch(
    "/gateway/merchants/{merchant_id}/verify",
    response_model=schemas.MerchantOut,
    summary="Verify a merchant account",
)
def verify_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    merchant.is_verified = True
    db.commit()
    db.refresh(merchant)
    return merchant


@router.patch(
    "/gateway/merchants/{merchant_id}/suspend",
    response_model=schemas.MerchantOut,
    summary="Suspend / deactivate a merchant",
)
def suspend_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    merchant.is_active = False
    db.commit()
    db.refresh(merchant)
    return merchant


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — PAYMENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/payments",
    response_model=List[schemas.PaymentOut],
    summary="All payments across all merchants",
)
def all_payments(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return (
        db.query(models.Payment)
        .order_by(models.Payment.created_at.desc())
        .limit(200)
        .all()
    )


@router.get(
    "/gateway/payments/flagged",
    response_model=List[schemas.PaymentOut],
    summary="Flagged / suspicious payments",
)
def flagged_payments(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return (
        db.query(models.Payment)
        .filter(models.Payment.is_flagged == True)
        .order_by(models.Payment.created_at.desc())
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — REFUNDS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/refunds",
    response_model=List[schemas.RefundOut],
    summary="All refunds",
)
def all_refunds(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return (
        db.query(models.Refund)
        .order_by(models.Refund.created_at.desc())
        .limit(200)
        .all()
    )
