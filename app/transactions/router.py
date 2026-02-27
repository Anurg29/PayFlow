"""
/transactions — Create, Get, List, Refund (MongoDB).

RBAC:
  - Any authenticated user can create transactions
  - Users see only their own transaction history
  - Only admin can refund transactions
"""

import random
import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from .. import models, schemas
from ..schemas import serialize_doc
from ..auth.router import get_current_user
from ..cache import get_cached_transaction, set_cached_transaction, invalidate_transaction
from .service import check_anomalies

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _txn_to_dict(txn: dict) -> dict:
    """Prepare a transaction dict for caching / response."""
    return {
        "id": str(txn["_id"]),
        "amount": txn["amount"],
        "payment_method": txn["payment_method"],
        "status": txn["status"],
        "idempotency_key": txn["idempotency_key"],
        "is_flagged": txn["is_flagged"],
        "user_id": str(txn["user_id"]),
        "merchant_id": str(txn.get("merchant_id")) if txn.get("merchant_id") else None,
        "admin_id": str(txn.get("admin_id")) if txn.get("admin_id") else None,
        "created_at": txn["created_at"].isoformat() if isinstance(txn["created_at"], datetime.datetime) else str(txn["created_at"]),
    }


# ── POST /transactions/ — Create new payment ──────────────────────────────────
@router.post("/", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: schemas.TransactionCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    col = db[models.TRANSACTIONS]

    # Idempotency check
    existing = col.find_one({"idempotency_key": payload.idempotency_key})
    if existing:
        return serialize_doc(existing)

    # Validate payment method
    valid_methods = {"upi", "card", "netbanking"}
    if payload.payment_method.lower() not in valid_methods:
        raise HTTPException(status_code=400, detail=f"Invalid payment_method. Choose from: {valid_methods}")

    # Anomaly detection
    is_flagged = check_anomalies(db, current_user["id"], payload.amount)

    # Simulate synchronous outcome
    # 95% success rate
    outcome = models.TransactionStatus.SUCCESS if random.random() < 0.95 else models.TransactionStatus.FAILED
    
    # Create transaction
    doc = {
        "amount": payload.amount,
        "payment_method": payload.payment_method.lower(),
        "idempotency_key": payload.idempotency_key,
        "status": outcome,
        "is_flagged": is_flagged,
        "user_id": current_user["id"],
        "created_at": datetime.datetime.utcnow(),
    }
    result = col.insert_one(doc)
    doc["_id"] = result.inserted_id

    # Cache it
    set_cached_transaction(str(doc["_id"]), _txn_to_dict(doc))

    return serialize_doc(doc)


# ── GET /transactions/ — List transactions ─────────────────────────────────────
@router.get("/", response_model=list[schemas.TransactionOut])
def list_transactions(db=Depends(get_db), current_user=Depends(get_current_user)):
    col = db[models.TRANSACTIONS]

    # Admin sees all, user sees only own
    if current_user.get("role") == models.UserRole.ADMIN:
        cursor = col.find().sort("created_at", -1)
    elif current_user.get("role") == models.UserRole.MERCHANT:
        cursor = col.find({"$or": [{"user_id": current_user["id"]}, {"merchant_id": current_user["id"]}]}).sort("created_at", -1)
    else:
        cursor = col.find({"user_id": current_user["id"]}).sort("created_at", -1)

    return [serialize_doc(t) for t in cursor]


# ── GET /transactions/{id} — Get by ID ─────────────────────────────────────────
@router.get("/{txn_id}", response_model=schemas.TransactionOut)
def get_transaction(txn_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    # Try cache first
    cached = get_cached_transaction(txn_id)
    if cached and cached["user_id"] == current_user["id"]:
        return cached

    try:
        oid = ObjectId(txn_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    txn = db[models.TRANSACTIONS].find_one({"_id": oid})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if str(txn["user_id"]) != current_user["id"] and current_user.get("role") != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = serialize_doc(txn)
    set_cached_transaction(txn_id, _txn_to_dict(txn))
    return result


# ── POST /transactions/{id}/refund — Admin only ───────────────────────────────
@router.post("/{txn_id}/refund", response_model=schemas.TransactionOut)
def refund_transaction(txn_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    # ── RBAC: admin-only refunds ──
    if current_user.get("role") != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can process refunds",
        )

    try:
        oid = ObjectId(txn_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    txn = db[models.TRANSACTIONS].find_one({"_id": oid})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn["status"] != models.TransactionStatus.SUCCESS:
        raise HTTPException(status_code=400, detail=f"Cannot refund a transaction with status '{txn['status']}'")

    db[models.TRANSACTIONS].update_one({"_id": oid}, {"$set": {"status": models.TransactionStatus.REFUNDED}})
    txn["status"] = models.TransactionStatus.REFUNDED

    invalidate_transaction(txn_id)

    return serialize_doc(txn)
