from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .models import UserRole


# ─── User Schemas ────────────────────────────────────────────────────────────

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


# ─── Token Schemas ────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ─── Transaction Schemas ──────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    amount: float
    payment_method: str   # upi | card | netbanking
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


# ─── Admin / Stats ────────────────────────────────────────────────────────────

class TransactionStats(BaseModel):
    total_transactions: int
    total_amount: float
    success_count: int
    failed_count: int
    flagged_count: int
