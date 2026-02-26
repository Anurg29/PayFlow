"""
PayFlow Schemas — Pydantic I/O models for all endpoints.
Adapted for MongoDB (ObjectId → str serialization).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from .models import UserRole


# ─── MongoDB ObjectId Helper ──────────────────────────────────────────────────

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document for JSON output — _id → id as string."""
    if doc is None:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# ─── User / Auth ──────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    email: str
    role: Optional[UserRole] = UserRole.USER


class UserCreate(UserBase):
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: Optional[str] = "user"

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
    id: str
    user_id: str
    business_name: str
    business_email: str
    website: Optional[str] = None
    webhook_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ─── API Keys ─────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    label: Optional[str] = "Default Key"


class ApiKeyOut(BaseModel):
    id: str
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
    notes: Optional[str] = None


class OrderOut(BaseModel):
    id: str
    order_ref: str
    amount: int
    currency: str
    status: str
    receipt: Optional[str] = None
    notes: Optional[str] = None
    attempts: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Payments ─────────────────────────────────────────────────────────────────

class PaymentCheckoutRequest(BaseModel):
    order_ref: str
    method: str
    email: Optional[str] = None
    contact: Optional[str] = None
    vpa: Optional[str] = None
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None
    card_name: Optional[str] = None


class PaymentOut(BaseModel):
    id: str
    payment_ref: str
    order_id: str
    amount: int
    currency: str
    method: str
    status: str
    email: Optional[str] = None
    contact: Optional[str] = None
    vpa: Optional[str] = None
    card_number_masked: Optional[str] = None
    card_network: Optional[str] = None
    amount_refunded: int = 0
    is_flagged: bool = False
    created_at: datetime
    captured_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Refunds ──────────────────────────────────────────────────────────────────

class RefundCreate(BaseModel):
    amount: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class RefundOut(BaseModel):
    id: str
    refund_ref: str
    payment_id: str
    amount: int
    status: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Webhook ──────────────────────────────────────────────────────────────────

class WebhookLogOut(BaseModel):
    id: str
    event_type: str
    target_url: str
    success: bool
    response_status: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Legacy Transaction ───────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    amount: float
    payment_method: str
    idempotency_key: str


class TransactionOut(BaseModel):
    id: str
    amount: float
    payment_method: str
    status: str
    idempotency_key: str
    is_flagged: bool
    user_id: str
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


# ─── Revenue Dashboard ────────────────────────────────────────────────────────

class RevenueBucket(BaseModel):
    period: str
    total_gmv_paise: int
    total_refunds_paise: int
    net_revenue_paise: int
    transaction_count: int
    success_count: int
    failed_count: int
    refund_count: int
    success_rate: float
    refund_rate: float


class RevenueDashboard(BaseModel):
    period_type: str
    buckets: list[RevenueBucket]
    total_gmv_paise: int
    total_refunds_paise: int
    total_net_paise: int
    overall_success_rate: float
    overall_refund_rate: float


# ─── Tax / GST Report ─────────────────────────────────────────────────────────

class GSTLineItem(BaseModel):
    month: str
    gross_revenue_paise: int
    refunds_paise: int
    net_taxable_paise: int
    cgst_paise: int
    sgst_paise: int
    igst_paise: int
    total_gst_paise: int
    total_with_gst_paise: int
    transaction_count: int


class GSTReport(BaseModel):
    financial_year: str
    gst_rate_percent: float
    line_items: list[GSTLineItem]
    total_gross_paise: int
    total_refunds_paise: int
    total_net_taxable_paise: int
    total_gst_paise: int
