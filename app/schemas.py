"""
PayFlow Schemas — Pydantic I/O models for all endpoints.
"""

from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from .models import UserRole


# ─── User / Auth ──────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    email: str
    role: Optional[UserRole] = UserRole.USER


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ─── Merchant ─────────────────────────────────────────────────────────────────

class MerchantCreate(BaseModel):
    business_name: str
    business_email: str
    website: Optional[str] = None
    webhook_url: Optional[str] = None


class MerchantUpdate(BaseModel):
    business_name: Optional[str] = None
    website: Optional[str] = None
    webhook_url: Optional[str] = None


class MerchantOut(BaseModel):
    id: int
    user_id: int
    business_name: str
    business_email: str
    website: Optional[str]
    webhook_url: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── API Keys ─────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    label: Optional[str] = "Default Key"


class ApiKeyOut(BaseModel):
    id: int
    key_id: str
    label: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreatedOut(ApiKeyOut):
    """Only returned ONCE at creation — includes the raw secret."""
    key_secret: str


# ─── Orders (Merchant→PayFlow) ────────────────────────────────────────────────

class OrderCreate(BaseModel):
    amount: int                          # in paise (₹1 = 100)
    currency: Optional[str] = "INR"
    receipt: Optional[str] = None
    notes: Optional[str] = None         # free-form JSON string


class OrderOut(BaseModel):
    id: int
    order_ref: str
    amount: int
    currency: str
    status: str
    receipt: Optional[str]
    notes: Optional[str]
    attempts: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Payments ─────────────────────────────────────────────────────────────────

class PaymentCheckoutRequest(BaseModel):
    """Sent by the checkout page / SDK when user submits payment."""
    order_ref: str
    method: str                          # upi | card | netbanking | wallet
    email: Optional[str] = None
    contact: Optional[str] = None
    # UPI
    vpa: Optional[str] = None
    # Card
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None
    card_name: Optional[str] = None


class PaymentOut(BaseModel):
    id: int
    payment_ref: str
    order_id: int
    amount: int
    currency: str
    method: str
    status: str
    email: Optional[str]
    contact: Optional[str]
    vpa: Optional[str]
    card_number_masked: Optional[str]
    card_network: Optional[str]
    amount_refunded: int
    is_flagged: bool
    created_at: datetime
    captured_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Refunds ──────────────────────────────────────────────────────────────────

class RefundCreate(BaseModel):
    amount: Optional[int] = None        # None = full refund
    reason: Optional[str] = None
    notes: Optional[str] = None


class RefundOut(BaseModel):
    id: int
    refund_ref: str
    payment_id: int
    amount: int
    status: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Webhook ──────────────────────────────────────────────────────────────────

class WebhookLogOut(BaseModel):
    id: int
    event_type: str
    target_url: str
    success: bool
    response_status: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Legacy Transaction ───────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    amount: float
    payment_method: str
    idempotency_key: str


class TransactionOut(BaseModel):
    id: int
    amount: float
    payment_method: str
    status: str
    idempotency_key: str
    is_flagged: bool
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Admin Stats ──────────────────────────────────────────────────────────────

class TransactionStats(BaseModel):
    total_transactions: int
    total_amount: float
    success_count: int
    failed_count: int
    flagged_count: int


class GatewayStats(BaseModel):
    total_merchants: int
    total_orders: int
    total_payments: int
    total_volume_paise: int
    total_refunds: int
