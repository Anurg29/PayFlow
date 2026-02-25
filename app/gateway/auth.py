"""
API Key authentication dependency for PayFlow Gateway.
Merchants pass:  Authorization: Basic <base64(key_id:key_secret)>
"""

import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from .. import models
from .keys import verify_secret

security = HTTPBasic()


def get_merchant_from_api_key(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.Merchant:
    """
    Validates key_id (username) and key_secret (password).
    Returns the Merchant object if valid.
    """
    key_id = credentials.username
    key_secret = credentials.password

    api_key = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.key_id == key_id, models.ApiKey.is_active == True)
        .first()
    )

    if not api_key or not verify_secret(key_secret, api_key.key_secret_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Update last used
    api_key.last_used_at = datetime.utcnow()
    db.commit()

    merchant = db.query(models.Merchant).filter(
        models.Merchant.id == api_key.merchant_id,
        models.Merchant.is_active == True,
    ).first()

    if not merchant:
        raise HTTPException(status_code=403, detail="Merchant account inactive or not found")

    return merchant
