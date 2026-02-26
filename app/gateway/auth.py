"""
API Key authentication dependency for PayFlow Gateway (MongoDB).
Merchants pass:  Authorization: Basic <base64(key_id:key_secret)>
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
from bson import ObjectId

from ..database import get_db
from .. import models
from .keys import verify_secret

security = HTTPBasic()


def get_merchant_from_api_key(
    credentials: HTTPBasicCredentials = Depends(security),
    db = Depends(get_db),
) -> dict:
    """
    Validates key_id (username) and key_secret (password).
    Returns the Merchant document if valid.
    """
    key_id = credentials.username
    key_secret = credentials.password

    api_key = db[models.API_KEYS].find_one({
        "key_id": key_id,
        "is_active": True
    })

    if not api_key or not verify_secret(key_secret, api_key["key_secret_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Update last used
    db[models.API_KEYS].update_one(
        {"_id": api_key["_id"]},
        {"$set": {"last_used_at": datetime.utcnow()}}
    )

    merchant = db[models.MERCHANTS].find_one({
        "_id": ObjectId(api_key["merchant_id"]),
        "is_active": True,
    })

    if not merchant:
        raise HTTPException(status_code=403, detail="Merchant account inactive or not found")

    return merchant
