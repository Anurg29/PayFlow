"""
PayFlow Gateway API — v1 (MongoDB)
Endpoints that MERCHANT apps call (authenticated via API key).

Base path: /v1
"""

import datetime
from bson import ObjectId
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from ..database import get_db
from .. import models, schemas
from ..schemas import serialize_doc
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
)
def create_order(
    payload: schemas.OrderCreate,
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0 paise")
    if payload.currency not in {"INR", "USD", "EUR"}:
        raise HTTPException(status_code=400, detail="Unsupported currency. Use INR, USD, or EUR")

    doc = {
        "order_ref": generate_order_ref(),
        "merchant_id": str(merchant["_id"]),
        "amount": payload.amount,
        "currency": payload.currency,
        "receipt": payload.receipt,
        "notes": payload.notes,
        "status": models.OrderStatus.CREATED,
        "attempts": 0,
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
        "created_at": datetime.datetime.utcnow(),
    }
    result = db[models.ORDERS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


@router.get(
    "/orders/{order_ref}",
    response_model=schemas.OrderOut,
    summary="Fetch an order",
)
def get_order(
    order_ref: str,
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    order = db[models.ORDERS].find_one({
        "order_ref": order_ref,
        "merchant_id": str(merchant["_id"]),
    })
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_doc(order)


@router.get(
    "/orders",
    response_model=List[schemas.OrderOut],
    summary="List all orders",
)
def list_orders(
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    cursor = (
        db[models.ORDERS].find({"merchant_id": str(merchant["_id"])})
        .sort("created_at", -1)
        .limit(100)
    )
    return [serialize_doc(o) for o in cursor]


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
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    payment = db[models.PAYMENTS].find_one({"payment_ref": payment_ref})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Verify order belongs to this merchant
    order = db[models.ORDERS].find_one({"_id": ObjectId(payment["order_id"]), "merchant_id": str(merchant["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Payment not found")

    return serialize_doc(payment)


@router.get(
    "/orders/{order_ref}/payments",
    response_model=List[schemas.PaymentOut],
    summary="List payments for an order",
)
def list_order_payments(
    order_ref: str,
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    order = db[models.ORDERS].find_one({
        "order_ref": order_ref,
        "merchant_id": str(merchant["_id"]),
    })
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    cursor = db[models.PAYMENTS].find({"order_id": str(order["_id"])})
    return [serialize_doc(p) for p in cursor]


@router.post(
    "/payments/{payment_ref}/capture",
    response_model=schemas.PaymentOut,
    summary="Capture an authorized payment",
)
def capture_payment(
    payment_ref: str,
    background_tasks: BackgroundTasks,
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    payment = db[models.PAYMENTS].find_one({"payment_ref": payment_ref})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    order = db[models.ORDERS].find_one({"_id": ObjectId(payment["order_id"]), "merchant_id": str(merchant["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.get("status") != models.PaymentStatus.AUTHORIZED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot capture payment in status '{payment.get('status')}'"
        )

    db[models.PAYMENTS].update_one(
        {"_id": payment["_id"]},
        {"$set": {"status": models.PaymentStatus.CAPTURED, "captured_at": datetime.datetime.utcnow()}}
    )
    payment["status"] = models.PaymentStatus.CAPTURED
    payment["captured_at"] = datetime.datetime.utcnow()

    db[models.ORDERS].update_one(
        {"_id": order["_id"]},
        {"$set": {"status": models.OrderStatus.PAID}}
    )

    background_tasks.add_task(
        dispatch_webhook, merchant["_id"], "payment.captured",
        {"payment_ref": payment["payment_ref"], "amount": payment["amount"]}
    )
    
    return serialize_doc(payment)


# ─────────────────────────────────────────────────────────────────────────────
# REFUNDS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/payments/{payment_ref}/refund",
    response_model=schemas.RefundOut,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a refund",
)
def create_refund(
    payment_ref: str,
    payload: schemas.RefundCreate,
    background_tasks: BackgroundTasks,
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    payment = db[models.PAYMENTS].find_one({"payment_ref": payment_ref})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    order = db[models.ORDERS].find_one({"_id": ObjectId(payment["order_id"]), "merchant_id": str(merchant["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.get("status") not in {models.PaymentStatus.CAPTURED, models.PaymentStatus.AUTHORIZED}:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund payment with status '{payment.get('status')}'"
        )

    amt_refunded = payment.get("amount_refunded", 0)
    refund_amount = payload.amount or (payment["amount"] - amt_refunded)
    remaining = payment["amount"] - amt_refunded

    if refund_amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Refund amount {refund_amount} exceeds refundable amount {remaining}"
        )

    refund = {
        "refund_ref": generate_refund_ref(),
        "payment_id": str(payment["_id"]),
        "amount": refund_amount,
        "reason": payload.reason,
        "notes": payload.notes,
        "status": "processed",
        "created_at": datetime.datetime.utcnow(),
        "processed_at": datetime.datetime.utcnow(),
    }
    r = db[models.REFUNDS].insert_one(refund)
    refund["_id"] = r.inserted_id

    new_refunded = amt_refunded + refund_amount
    new_status = models.PaymentStatus.REFUNDED if new_refunded >= payment["amount"] else payment["status"]
    
    db[models.PAYMENTS].update_one(
        {"_id": payment["_id"]},
        {
            "$set": {
                "amount_refunded": new_refunded,
                "status": new_status,
                "refund_status": "full" if new_refunded >= payment["amount"] else "partial"
            }
        }
    )

    background_tasks.add_task(
        dispatch_webhook, merchant["_id"], "refund.processed",
        {"refund_ref": refund["refund_ref"], "amount": refund["amount"]}
    )
    
    return serialize_doc(refund)


@router.get(
    "/payments/{payment_ref}/refunds",
    response_model=List[schemas.RefundOut],
    summary="List refunds for a payment",
)
def list_refunds(
    payment_ref: str,
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    payment = db[models.PAYMENTS].find_one({"payment_ref": payment_ref})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    order = db[models.ORDERS].find_one({"_id": ObjectId(payment["order_id"]), "merchant_id": str(merchant["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Payment not found")

    cursor = db[models.REFUNDS].find({"payment_id": str(payment["_id"])})
    return [serialize_doc(r) for r in cursor]


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK LOGS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/webhooks/logs",
    response_model=List[schemas.WebhookLogOut],
    summary="View webhook delivery logs",
)
def webhook_logs(
    merchant: dict = Depends(get_merchant_from_api_key),
    db = Depends(get_db),
):
    cursor = (
        db[models.WEBHOOK_LOGS].find({"merchant_id": str(merchant["_id"])})
        .sort("created_at", -1)
        .limit(50)
    )
    return [serialize_doc(w) for w in cursor]
