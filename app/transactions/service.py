"""
Anomaly detection service.
Rules (from README):
  1. High Value   — amount > ₹50,000          → flag + allow
  2. Duplicate    — same amount within 60 s    → flag + allow
  3. High Frequency — >5 transactions in 60 s  → flag + allow
"""

import datetime
from sqlalchemy.orm import Session
from .. import models


def check_anomalies(db: Session, user_id: int, amount: float) -> bool:
    is_flagged = False

    # Rule 1: High Value
    if amount > 50_000:
        is_flagged = True

    # Time window
    one_minute_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)

    recent_txns = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.created_at >= one_minute_ago,
        )
        .all()
    )

    # Rule 2: Duplicate transaction (same amount in last 60 s)
    for txn in recent_txns:
        if txn.amount == amount:
            is_flagged = True
            break

    # Rule 3: High Frequency (>5 transactions in last 60 s)
    if len(recent_txns) >= 5:
        is_flagged = True

    return is_flagged
