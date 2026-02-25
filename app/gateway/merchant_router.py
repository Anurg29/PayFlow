"""
Merchant management routes — onboarding, API key CRUD.
Authenticated via JWT (same as regular users, but role=merchant).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..auth.router import get_current_user
from .keys import generate_key_pair, hash_secret

router = APIRouter(prefix="/merchants", tags=["Merchant Onboarding"])


def _require_merchant_role(current_user: models.User = Depends(get_current_user)):
    if current_user.role not in {models.UserRole.MERCHANT, models.UserRole.ADMIN}:
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
    description=(
        "Register an existing user account as a PayFlow merchant. "
        "User role must be `merchant`. After registration, generate API keys to start accepting payments."
    ),
)
def register_merchant(
    payload: schemas.MerchantCreate,
    current_user: models.User = Depends(_require_merchant_role),
    db: Session = Depends(get_db),
):
    if current_user.merchant_profile:
        raise HTTPException(status_code=400, detail="Merchant profile already exists")

    existing = db.query(models.Merchant).filter(
        models.Merchant.business_email == payload.business_email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Business email already registered")

    merchant = models.Merchant(
        user_id=current_user.id,
        business_name=payload.business_name,
        business_email=payload.business_email,
        website=payload.website,
        webhook_url=payload.webhook_url,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


@router.get(
    "/me",
    response_model=schemas.MerchantOut,
    summary="Get your merchant profile",
)
def get_my_merchant(
    current_user: models.User = Depends(_require_merchant_role),
    db: Session = Depends(get_db),
):
    if not current_user.merchant_profile:
        raise HTTPException(status_code=404, detail="Merchant profile not found. Register first.")
    return current_user.merchant_profile


@router.patch(
    "/me",
    response_model=schemas.MerchantOut,
    summary="Update merchant profile",
)
def update_merchant(
    payload: schemas.MerchantUpdate,
    current_user: models.User = Depends(_require_merchant_role),
    db: Session = Depends(get_db),
):
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    if payload.business_name:
        merchant.business_name = payload.business_name
    if payload.website is not None:
        merchant.website = payload.website
    if payload.webhook_url is not None:
        merchant.webhook_url = payload.webhook_url

    db.commit()
    db.refresh(merchant)
    return merchant


# ─── API Keys ─────────────────────────────────────────────────────────────────

@router.post(
    "/me/keys",
    response_model=schemas.ApiKeyCreatedOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate new API key pair",
    description=(
        "Generates a new `key_id` and `key_secret`. "
        "**The `key_secret` is shown only once** — store it immediately. "
        "Use `key_id:key_secret` as HTTP Basic Auth credentials for the Gateway API."
    ),
)
def create_api_key(
    payload: schemas.ApiKeyCreate,
    current_user: models.User = Depends(_require_merchant_role),
    db: Session = Depends(get_db),
):
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    key_id, key_secret = generate_key_pair()
    key_secret_hash = hash_secret(key_secret)

    api_key = models.ApiKey(
        merchant_id=merchant.id,
        key_id=key_id,
        key_secret_hash=key_secret_hash,
        label=payload.label,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "key_id": api_key.key_id,
        "key_secret": key_secret,       # raw — shown once
        "label": api_key.label,
        "is_active": api_key.is_active,
        "created_at": api_key.created_at,
    }


@router.get(
    "/me/keys",
    response_model=List[schemas.ApiKeyOut],
    summary="List your API keys",
)
def list_api_keys(
    current_user: models.User = Depends(_require_merchant_role),
    db: Session = Depends(get_db),
):
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")
    return merchant.api_keys


@router.delete(
    "/me/keys/{key_id}",
    summary="Revoke an API key",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_api_key(
    key_id: str,
    current_user: models.User = Depends(_require_merchant_role),
    db: Session = Depends(get_db),
):
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    api_key = db.query(models.ApiKey).filter(
        models.ApiKey.key_id == key_id,
        models.ApiKey.merchant_id == merchant.id,
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()
