"""
Fraud detection for PayFlow Gateway payments.
Rules:
  1. High Value     — amount > ₹50,000 (5,000,000 paise)
  2. Duplicate      — same amount for same merchant within 60 s
  3. High Frequency — >5 payment attempts in 60 s for same order
  4. Invalid VPA    — UPI VPA doesn't contain @
  5. Velocity       — merchant's total payments > 50 in last minute
"""

import datetime
from sqlalchemy.orm import Session
from .. import models


def check_payment_fraud(
    db: Session,
    order: models.Order,
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
    recent_payments = (
        db.query(models.Payment)
        .filter(
            models.Payment.order_id == order.id,
            models.Payment.created_at >= one_minute_ago,
        )
        .all()
    )
    same_amount = [p for p in recent_payments if p.amount == amount]
    if same_amount:
        reasons.append("duplicate_amount")
    if len(recent_payments) >= 5:
        reasons.append("high_frequency")

    # Rule 4: Invalid VPA for UPI
    if method == "upi" and vpa and "@" not in vpa:
        reasons.append("invalid_vpa")

    # Rule 5: Merchant-level velocity
    recent_merchant_payments = (
        db.query(models.Payment)
        .join(models.Order, models.Payment.order_id == models.Order.id)
        .filter(
            models.Order.merchant_id == order.merchant_id,
            models.Payment.created_at >= one_minute_ago,
        )
        .count()
    )
    if recent_merchant_payments >= 50:
        reasons.append("merchant_velocity")

    is_flagged = bool(reasons)
    flag_reason = ",".join(reasons) if reasons else None
    return is_flagged, flag_reason
