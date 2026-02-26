"""
Fraud detection for PayFlow Gateway payments. (MongoDB)
Rules:
  1. High Value     — amount > ₹50,000 (5,000,000 paise)
  2. Duplicate      — same amount for same merchant within 60 s
  3. High Frequency — >5 payment attempts in 60 s for same order
  4. Invalid VPA    — UPI VPA doesn't contain @
  5. Velocity       — merchant's total payments > 50 in last minute
"""

import datetime
from .. import models
from bson import ObjectId

def check_payment_fraud(
    db,
    order: dict,
    amount: int,
    method: str,
    vpa: str | None = None,
) -> tuple[bool, str | None]:
    """
    Returns (is_flagged, flag_reason).
    """
    reasons = []

    # Rule 1: High value (₹50,000 = 5,000,000 paise)
    if amount > 5_000_000:
        reasons.append("high_value")

    # Time window
    one_minute_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)

    # Rule 2 & 3: Duplicate / High Frequency on this order
    recent_payments = list(
        db[models.PAYMENTS].find({
            "order_id": str(order["_id"]),
            "created_at": {"$gte": one_minute_ago}
        })
    )
    same_amount = [p for p in recent_payments if p.get("amount") == amount]
    if same_amount:
        reasons.append("duplicate_amount")
    if len(recent_payments) >= 5:
        reasons.append("high_frequency")

    # Rule 4: Invalid VPA for UPI
    if method == "upi" and vpa and "@" not in vpa:
        reasons.append("invalid_vpa")

    # Rule 5: Merchant-level velocity
    # Find all orders in last min for this merchant
    recent_orders = list(db[models.ORDERS].find({
        "merchant_id": str(order["merchant_id"]),
        "created_at": {"$gte": one_minute_ago}
    }))
    order_ids = [str(o["_id"]) for o in recent_orders]
    
    recent_merchant_payments = db[models.PAYMENTS].count_documents({
        "order_id": {"$in": order_ids},
        "created_at": {"$gte": one_minute_ago}
    })
    
    if recent_merchant_payments >= 50:
        reasons.append("merchant_velocity")

    is_flagged = bool(reasons)
    flag_reason = ",".join(reasons) if reasons else None
    return is_flagged, flag_reason
