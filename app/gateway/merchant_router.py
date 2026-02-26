"""
Merchant management routes — onboarding, API key CRUD (MongoDB).
Authenticated via JWT (same as regular users, but role=merchant).
"""

from fastapi import APIRouter, Depends, HTTPException, status
import datetime
from typing import List
from bson import ObjectId

from ..database import get_db
from .. import models, schemas
from ..schemas import serialize_doc
from ..auth.router import get_current_user
from .keys import generate_key_pair, hash_secret

router = APIRouter(prefix="/merchants", tags=["Merchant Onboarding"])


def _require_merchant_role(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in {models.UserRole.MERCHANT, models.UserRole.ADMIN}:
        raise HTTPException(
            status_code=403,
            detail="Only merchant or admin accounts can access this resource",
        )
    return current_user


# ─── Merchant Profile ─────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=schemas.MerchantOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register as a merchant",
)
def register_merchant(
    payload: schemas.MerchantCreate,
    current_user: dict = Depends(_require_merchant_role),
    db = Depends(get_db),
):
    existing_merchant = db[models.MERCHANTS].find_one({"user_id": current_user["id"]})
    if existing_merchant:
        raise HTTPException(status_code=400, detail="Merchant profile already exists")

    existing_email = db[models.MERCHANTS].find_one({"business_email": payload.business_email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Business email already registered")

    doc = {
        "user_id": current_user["id"],
        "business_name": payload.business_name,
        "business_email": payload.business_email,
        "website": payload.website,
        "webhook_url": payload.webhook_url,
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.datetime.utcnow(),
    }
    result = db[models.MERCHANTS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


@router.get(
    "/me",
    response_model=schemas.MerchantOut,
    summary="Get your merchant profile",
)
def get_my_merchant(
    current_user: dict = Depends(_require_merchant_role),
    db = Depends(get_db),
):
    merchant = db[models.MERCHANTS].find_one({"user_id": current_user["id"]})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found. Register first.")
    return serialize_doc(merchant)


@router.patch(
    "/me",
    response_model=schemas.MerchantOut,
    summary="Update merchant profile",
)
def update_merchant(
    payload: schemas.MerchantUpdate,
    current_user: dict = Depends(_require_merchant_role),
    db = Depends(get_db),
):
    merchant = db[models.MERCHANTS].find_one({"user_id": current_user["id"]})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    update_fields = {}
    if payload.business_name:
        update_fields["business_name"] = payload.business_name
    if payload.website is not None:
        update_fields["website"] = payload.website
    if payload.webhook_url is not None:
        update_fields["webhook_url"] = payload.webhook_url

    if update_fields:
        db[models.MERCHANTS].update_one({"_id": merchant["_id"]}, {"$set": update_fields})
        merchant.update(update_fields)

    return serialize_doc(merchant)


# ─── API Keys ─────────────────────────────────────────────────────────────────

@router.post(
    "/me/keys",
    response_model=schemas.ApiKeyCreatedOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate new API key pair",
)
def create_api_key(
    payload: schemas.ApiKeyCreate,
    current_user: dict = Depends(_require_merchant_role),
    db = Depends(get_db),
):
    merchant = db[models.MERCHANTS].find_one({"user_id": current_user["id"]})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    key_id, key_secret = generate_key_pair()
    key_secret_hash = hash_secret(key_secret)

    api_key = {
        "merchant_id": str(merchant["_id"]),
        "key_id": key_id,
        "key_secret_hash": key_secret_hash,
        "label": payload.label,
        "is_active": True,
        "created_at": datetime.datetime.utcnow(),
    }
    result = db[models.API_KEYS].insert_one(api_key)
    api_key["_id"] = result.inserted_id

    return {
        "id": str(api_key["_id"]),
        "key_id": api_key["key_id"],
        "key_secret": key_secret,
        "label": api_key["label"],
        "is_active": api_key["is_active"],
        "created_at": api_key["created_at"],
    }


@router.get(
    "/me/keys",
    response_model=List[schemas.ApiKeyOut],
    summary="List your API keys",
)
def list_api_keys(
    current_user: dict = Depends(_require_merchant_role),
    db = Depends(get_db),
):
    merchant = db[models.MERCHANTS].find_one({"user_id": current_user["id"]})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")
        
    cursor = db[models.API_KEYS].find({"merchant_id": str(merchant["_id"])})
    return [serialize_doc(k) for k in cursor]


@router.delete(
    "/me/keys/{key_id}",
    summary="Revoke an API key",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(_require_merchant_role),
    db = Depends(get_db),
):
    merchant = db[models.MERCHANTS].find_one({"user_id": current_user["id"]})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    api_key = db[models.API_KEYS].find_one({
        "key_id": key_id,
        "merchant_id": str(merchant["_id"]),
    })
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    db[models.API_KEYS].update_one({"_id": api_key["_id"]}, {"$set": {"is_active": False}})
