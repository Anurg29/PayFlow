"""
Webhook dispatcher — sends signed events to merchant callback URLs (MongoDB).
"""

import json
import hmac
import hashlib
import httpx
import datetime
from bson import ObjectId

from ..database import get_db
from .. import models


def _sign_payload(payload_str: str, secret: str) -> str:
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_str.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return mac.hexdigest()


def dispatch_webhook(
    merchant_id: str | ObjectId,
    event_type: str,
    data: dict,
    signing_secret: str = "payflow_default_secret",
) -> None:
    """
    Fires a POST request to merchant's webhook_url with signed payload.
    Logs result in WebhookLog collection.
    Non-blocking best-effort — errors are logged, not raised.
    """
    db = get_db()
    merchant = db[models.MERCHANTS].find_one({"_id": ObjectId(merchant_id)})
    
    if not merchant or not merchant.get("webhook_url"):
        return

    payload = {
        "event": event_type,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "payload": data,
    }
    payload_str = json.dumps(payload, default=str)
    signature = _sign_payload(payload_str, signing_secret)

    headers = {
        "Content-Type": "application/json",
        "X-PayFlow-Signature": signature,
        "X-PayFlow-Event": event_type,
    }

    log = {
        "merchant_id": str(merchant["_id"]),
        "event_type": event_type,
        "payload": payload_str,
        "target_url": merchant["webhook_url"],
        "created_at": datetime.datetime.utcnow(),
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(merchant["webhook_url"], content=payload_str, headers=headers)
            log["response_status"] = resp.status_code
            log["response_body"] = resp.text[:500]
            log["success"] = 200 <= resp.status_code < 300
    except Exception as exc:
        log["response_body"] = str(exc)[:500]
        log["success"] = False

    db[models.WEBHOOK_LOGS].insert_one(log)
