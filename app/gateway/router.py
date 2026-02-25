"""
PayFlow Gateway API — v1
Endpoints that MERCHANT apps call (authenticated via API key).

Base path: /v1
"""

import json
import random
import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from .auth import get_merchant_from_api_key
from .keys import generate_order_ref, generate_payment_ref, generate_refund_ref
from .fraud import check_payment_fraud
from .webhooks import dispatch_webhook

router = APIRouter(prefix="/v1", tags=["Gateway API v1"])


# ─────────────────────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=schemas.OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order",
    description=(
        "**Step 1 of checkout flow.**\n\n"
        "Create an order with `amount` (in paise) and `currency`. "
        "Returns `order_ref` which you pass to the PayFlow Checkout JS SDK or redirect the user to "
        "`https://payflow.app/pay/{order_ref}`."
    ),
)
def create_order(
    payload: schemas.OrderCreate,
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0 paise")
    if payload.currency not in {"INR", "USD", "EUR"}:
        raise HTTPException(status_code=400, detail="Unsupported currency. Use INR, USD, or EUR")

    order = models.Order(
        order_ref=generate_order_ref(),
        merchant_id=merchant.id,
        amount=payload.amount,
        currency=payload.currency,
        receipt=payload.receipt,
        notes=payload.notes,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get(
    "/orders/{order_ref}",
    response_model=schemas.OrderOut,
    summary="Fetch an order",
)
def get_order(
    order_ref: str,
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    order = db.query(models.Order).filter(
        models.Order.order_ref == order_ref,
        models.Order.merchant_id == merchant.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get(
    "/orders",
    response_model=List[schemas.OrderOut],
    summary="List all orders",
)
def list_orders(
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Order)
        .filter(models.Order.merchant_id == merchant.id)
        .order_by(models.Order.created_at.desc())
        .limit(100)
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/payments/{payment_ref}",
    response_model=schemas.PaymentOut,
    summary="Fetch a payment",
)
def get_payment(
    payment_ref: str,
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(models.Payment)
        .join(models.Order, models.Payment.order_id == models.Order.id)
        .filter(
            models.Payment.payment_ref == payment_ref,
            models.Order.merchant_id == merchant.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get(
    "/orders/{order_ref}/payments",
    response_model=List[schemas.PaymentOut],
    summary="List payments for an order",
)
def list_order_payments(
    order_ref: str,
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    order = db.query(models.Order).filter(
        models.Order.order_ref == order_ref,
        models.Order.merchant_id == merchant.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.payments


@router.post(
    "/payments/{payment_ref}/capture",
    response_model=schemas.PaymentOut,
    summary="Capture an authorized payment",
    description=(
        "Captures a payment that is in `authorized` state. "
        "For most payment methods, PayFlow auto-captures. "
        "Use this for two-step auth flows."
    ),
)
def capture_payment(
    payment_ref: str,
    background_tasks: BackgroundTasks,
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(models.Payment)
        .join(models.Order)
        .filter(
            models.Payment.payment_ref == payment_ref,
            models.Order.merchant_id == merchant.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != models.PaymentStatus.AUTHORIZED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot capture payment in status '{payment.status}'"
        )

    payment.status = models.PaymentStatus.CAPTURED
    payment.captured_at = datetime.datetime.utcnow()

    # Update order status
    order = payment.order
    order.status = models.OrderStatus.PAID
    db.commit()
    db.refresh(payment)

    # Fire webhook
    background_tasks.add_task(
        dispatch_webhook, db, merchant,
        "payment.captured",
        {"payment_ref": payment.payment_ref, "amount": payment.amount},
    )
    return payment


# ─────────────────────────────────────────────────────────────────────────────
# REFUNDS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/payments/{payment_ref}/refund",
    response_model=schemas.RefundOut,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a refund",
    description=(
        "Refund a captured payment fully or partially. "
        "Leave `amount` empty for a full refund."
    ),
)
def create_refund(
    payment_ref: str,
    payload: schemas.RefundCreate,
    background_tasks: BackgroundTasks,
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(models.Payment)
        .join(models.Order)
        .filter(
            models.Payment.payment_ref == payment_ref,
            models.Order.merchant_id == merchant.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status not in {
        models.PaymentStatus.CAPTURED, models.PaymentStatus.AUTHORIZED
    }:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund payment with status '{payment.status}'"
        )

    refund_amount = payload.amount or (payment.amount - payment.amount_refunded)
    remaining = payment.amount - payment.amount_refunded

    if refund_amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Refund amount {refund_amount} exceeds refundable amount {remaining}"
        )

    refund = models.Refund(
        refund_ref=generate_refund_ref(),
        payment_id=payment.id,
        amount=refund_amount,
        reason=payload.reason,
        notes=payload.notes,
        status="processed",
        processed_at=datetime.datetime.utcnow(),
    )
    db.add(refund)

    payment.amount_refunded += refund_amount
    if payment.amount_refunded >= payment.amount:
        payment.status = models.PaymentStatus.REFUNDED
        payment.refund_status = "full"
    else:
        payment.refund_status = "partial"

    db.commit()
    db.refresh(refund)

    # Fire webhook
    background_tasks.add_task(
        dispatch_webhook, db, merchant,
        "refund.processed",
        {"refund_ref": refund.refund_ref, "amount": refund.amount},
    )
    return refund


@router.get(
    "/payments/{payment_ref}/refunds",
    response_model=List[schemas.RefundOut],
    summary="List refunds for a payment",
)
def list_refunds(
    payment_ref: str,
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(models.Payment)
        .join(models.Order)
        .filter(
            models.Payment.payment_ref == payment_ref,
            models.Order.merchant_id == merchant.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment.refunds


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK LOGS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/webhooks/logs",
    response_model=List[schemas.WebhookLogOut],
    summary="View webhook delivery logs",
)
def webhook_logs(
    merchant: models.Merchant = Depends(get_merchant_from_api_key),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.WebhookLog)
        .filter(models.WebhookLog.merchant_id == merchant.id)
        .order_by(models.WebhookLog.created_at.desc())
        .limit(50)
        .all()
    )
