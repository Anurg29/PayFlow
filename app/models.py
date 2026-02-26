"""
PayFlow — Document Models & Enums.

MongoDB is schemaless — these enums and collection name constants
ensure consistency across the codebase.
"""

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


# ─── Collection Names ─────────────────────────────────────────────────────────

USERS = "users"
MERCHANTS = "merchants"
API_KEYS = "api_keys"
ORDERS = "orders"
PAYMENTS = "payments"
REFUNDS = "refunds"
WEBHOOK_LOGS = "webhook_logs"
TRANSACTIONS = "transactions"
