"""
PayFlow — Database Models
Covers: Users, Merchants, API Keys, Orders, Payments, Webhooks
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, BigInteger
)
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MERCHANT = "merchant"
    USER = "user"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderStatus(str, enum.Enum):
    CREATED = "created"
    ATTEMPTED = "attempted"
    PAID = "paid"
    EXPIRED = "expired"


class PaymentStatus(str, enum.Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    FAILED = "failed"


class WebhookEventType(str, enum.Enum):
    PAYMENT_CAPTURED = "payment.captured"
    PAYMENT_FAILED = "payment.failed"
    ORDER_PAID = "order.paid"
    REFUND_PROCESSED = "refund.processed"


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.USER)

    transactions = relationship("Transaction", back_populates="owner")
    merchant_profile = relationship("Merchant", back_populates="user", uselist=False)


# ─── Merchant ─────────────────────────────────────────────────────────────────

class Merchant(Base):
    """Businesses / developers who use PayFlow as a payment gateway."""
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    business_name = Column(String, nullable=False)
    business_email = Column(String, unique=True, index=True)
    website = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)   # where we POST events
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="merchant_profile")
    api_keys = relationship("ApiKey", back_populates="merchant", cascade="all, delete")
    orders = relationship("Order", back_populates="merchant", cascade="all, delete")
    webhook_logs = relationship("WebhookLog", back_populates="merchant")


# ─── API Key ──────────────────────────────────────────────────────────────────

class ApiKey(Base):
    """key_id / key_secret pairs issued to merchants (like Razorpay)."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    key_id = Column(String, unique=True, index=True)      # pf_key_xxxxx
    key_secret_hash = Column(String)                       # bcrypt hash of secret
    label = Column(String, default="Default Key")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    merchant = relationship("Merchant", back_populates="api_keys")


# ─── Order ────────────────────────────────────────────────────────────────────

class Order(Base):
    """
    Merchant creates an order → user pays → order becomes PAID.
    Similar to Razorpay Orders API.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_ref = Column(String, unique=True, index=True)   # pf_order_xxxxx
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    amount = Column(BigInteger)           # amount in paise (₹1 = 100 paise)
    currency = Column(String, default="INR")
    status = Column(String, default=OrderStatus.CREATED)
    receipt = Column(String, nullable=True)               # merchant's receipt id
    notes = Column(Text, nullable=True)                   # JSON string
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    merchant = relationship("Merchant", back_populates="orders")
    payments = relationship("Payment", back_populates="order", cascade="all, delete")


# ─── Payment ──────────────────────────────────────────────────────────────────

class Payment(Base):
    """
    A payment attempt against an order.
    Similar to Razorpay Payments API.
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_ref = Column(String, unique=True, index=True)  # pf_pay_xxxxx
    order_id = Column(Integer, ForeignKey("orders.id"))
    amount = Column(BigInteger)                            # in paise
    currency = Column(String, default="INR")
    method = Column(String)                                # upi | card | netbanking | wallet
    status = Column(String, default=PaymentStatus.CREATED)

    # Payer info
    email = Column(String, nullable=True)
    contact = Column(String, nullable=True)

    # Card details (masked)
    card_number_masked = Column(String, nullable=True)
    card_network = Column(String, nullable=True)           # Visa, Mastercard, RuPay

    # UPI
    vpa = Column(String, nullable=True)                    # UPI VPA

    # Refund tracking
    amount_refunded = Column(BigInteger, default=0)
    refund_status = Column(String, nullable=True)

    # Fraud detection
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    captured_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete")


# ─── Refund ───────────────────────────────────────────────────────────────────

class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    refund_ref = Column(String, unique=True, index=True)   # pf_rfnd_xxxxx
    payment_id = Column(Integer, ForeignKey("payments.id"))
    amount = Column(BigInteger)                            # in paise
    status = Column(String, default="pending")             # pending | processed | failed
    reason = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    payment = relationship("Payment", back_populates="refunds")


# ─── Webhook Log ──────────────────────────────────────────────────────────────

class WebhookLog(Base):
    """Audit log of every webhook dispatch to merchant URLs."""
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    event_type = Column(String)
    payload = Column(Text)             # JSON string
    target_url = Column(String)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    merchant = relationship("Merchant", back_populates="webhook_logs")


# ─── Legacy Transaction (kept for backward compat) ───────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    payment_method = Column(String)
    status = Column(String, default=TransactionStatus.PENDING)
    idempotency_key = Column(String, unique=True, index=True)
    is_flagged = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="transactions")
