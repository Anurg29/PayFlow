"""
Anomaly detection service (MongoDB).
Rules:
  1. High Value   — amount > ₹50,000          → flag
  2. Duplicate    — same amount within 60 s    → flag
  3. High Frequency — >5 transactions in 60 s  → flag
"""

import datetime
from .. import models


def check_anomalies(db, user_id: str, amount: float) -> bool:
    is_flagged = False

    # Rule 1: High Value
    if amount > 50_000:
        is_flagged = True

    # Time window
    one_minute_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)

    recent = list(
        db[models.TRANSACTIONS].find({
            "user_id": user_id,
            "created_at": {"$gte": one_minute_ago},
        })
    )

    # Rule 2: Duplicate (same amount in last 60s)
    for txn in recent:
        if txn["amount"] == amount:
            is_flagged = True
            break

    # Rule 3: High Frequency (>5 in last 60s)
    if len(recent) >= 5:
        is_flagged = True

    return is_flagged
