"""
Razorpay Service — wraps the official Razorpay Python SDK.

Flow:
  1. Merchant calls POST /v1/orders  → we call rzp.order.create()  → get rzp_order_id
  2. Frontend opens Razorpay Checkout.js with rzp_order_id + key_id
  3. Customer pays → Razorpay calls POST /pay/{order_ref}/verify with
       razorpay_payment_id, razorpay_order_id, razorpay_signature
  4. We verify HMAC-SHA256 signature → mark payment as CAPTURED

Env vars required:
  RAZORPAY_KEY_ID     — from dashboard.razorpay.com/app/keys
  RAZORPAY_KEY_SECRET — same page (keep secret!)
"""

import hmac
import hashlib
import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# ── Razorpay client (singleton) ───────────────────────────────────────────────

def _get_client() -> razorpay.Client:
    """Returns an authenticated Razorpay client. Raises if keys not set."""
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError(
            "Razorpay keys not configured. "
            "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your .env file."
        )
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def is_razorpay_configured() -> bool:
    """True when both Razorpay keys are present in the environment."""
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


# ── Order ──────────────────────────────────────────────────────────────────────

def create_razorpay_order(amount_paise: int, currency: str, receipt: str) -> dict:
    """
    Creates a real Razorpay order.

    Args:
        amount_paise: Amount in smallest currency unit (paise for INR).
        currency:     ISO 4217 code — 'INR', 'USD', etc.
        receipt:      Your internal receipt/order identifier.

    Returns:
        Razorpay order dict with keys: id, amount, currency, status, receipt, ...
    
    Raises:
        razorpay.errors.BadRequestError: on invalid params
        RuntimeError: when keys not configured
    """
    client = _get_client()
    order_data = {
        "amount":   amount_paise,
        "currency": currency,
        "receipt":  receipt,
        "payment_capture": 1,   # Auto-capture payment (no manual capture needed)
    }
    return client.order.create(data=order_data)


# ── Signature Verification ─────────────────────────────────────────────────────

def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """
    Verifies the HMAC-SHA256 signature Razorpay sends after payment.

    The message is: razorpay_order_id + '|' + razorpay_payment_id
    Signed with RAZORPAY_KEY_SECRET.

    Returns True if signature is valid, False otherwise.
    """
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        key=RAZORPAY_KEY_SECRET.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature)


# ── Payment Fetch ──────────────────────────────────────────────────────────────

def fetch_razorpay_payment(payment_id: str) -> dict:
    """
    Fetches payment details from Razorpay by payment_id.
    Useful for webhook reconciliation.
    """
    client = _get_client()
    return client.payment.fetch(payment_id)


# ── Refund ────────────────────────────────────────────────────────────────────

def create_razorpay_refund(
    razorpay_payment_id: str,
    amount_paise: int | None = None,
    notes: dict | None = None,
) -> dict:
    """
    Issues a refund on a Razorpay payment.

    Args:
        razorpay_payment_id: The rzp_pay_xxx ID to refund.
        amount_paise:        Partial amount to refund (paise). None = full refund.
        notes:               Optional dict of notes attached to the refund.

    Returns:
        Razorpay refund dict.
    """
    client = _get_client()
    data: dict = {}
    if amount_paise:
        data["amount"] = amount_paise
    if notes:
        data["notes"] = notes
    return client.payment.refund(razorpay_payment_id, data)
