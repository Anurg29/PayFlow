"""
Hosted Checkout Router — /pay/{order_ref} (MongoDB)
End-users land here to complete payment.
"""

import random
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from bson import ObjectId

from ..database import get_db
from .. import models, schemas
from ..schemas import serialize_doc
from .keys import generate_payment_ref
from .fraud import check_payment_fraud

router = APIRouter(prefix="/pay", tags=["Hosted Checkout"])


# ─── Initiate payment (called by payflow.js SDK) ──────────────────────────────

@router.post(
    "/{order_ref}",
    response_model=schemas.PaymentOut,
    summary="Submit payment for an order",
)
def submit_payment(
    order_ref: str,
    payload: schemas.PaymentCheckoutRequest,
    db = Depends(get_db),
):
    # Validate order
    order = db[models.ORDERS].find_one({"order_ref": order_ref})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.get("status") == models.OrderStatus.PAID:
        raise HTTPException(status_code=400, detail="Order already paid")
        
    if order.get("expires_at") and order["expires_at"] < datetime.datetime.utcnow():
        db[models.ORDERS].update_one({"_id": order["_id"]}, {"$set": {"status": models.OrderStatus.EXPIRED}})
        raise HTTPException(status_code=400, detail="Order has expired")

    # Validate method
    valid_methods = {"upi", "card", "netbanking", "wallet"}
    if payload.method.lower() not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid method. Choose from: {valid_methods}"
        )

    # Fraud detection
    is_flagged, flag_reason = check_payment_fraud(
        db=db,
        order=order,
        amount=order.get("amount", 0),
        method=payload.method.lower(),
        vpa=payload.vpa,
    )

    # Mask card number
    card_masked = None
    card_network = None
    if payload.card_number:
        digits = payload.card_number.replace(" ", "").replace("-", "")
        card_masked = f"{'*' * (len(digits) - 4)}{digits[-4:]}"
        # Detect network by first digit
        network_map = {"4": "Visa", "5": "Mastercard", "6": "RuPay", "3": "Amex"}
        card_network = network_map.get(digits[0], "Unknown")

    # Update attempt count
    db[models.ORDERS].update_one(
        {"_id": order["_id"]},
        {"$inc": {"attempts": 1}, "$set": {"status": models.OrderStatus.ATTEMPTED}}
    )

    # Simulate gateway outcome (96% success)
    success = random.random() < 0.96
    pay_status = models.PaymentStatus.CAPTURED if success else models.PaymentStatus.FAILED

    payment = {
        "payment_ref": generate_payment_ref(),
        "order_id": str(order["_id"]),
        "amount": order.get("amount", 0),
        "currency": order.get("currency", "INR"),
        "method": payload.method.lower(),
        "status": pay_status,
        "email": payload.email,
        "contact": payload.contact,
        "vpa": payload.vpa,
        "card_number_masked": card_masked,
        "card_network": card_network,
        "is_flagged": is_flagged,
        "flag_reason": flag_reason,
        "captured_at": datetime.datetime.utcnow() if success else None,
        "created_at": datetime.datetime.utcnow(),
        "amount_refunded": 0,
    }
    result = db[models.PAYMENTS].insert_one(payment)
    payment["_id"] = result.inserted_id

    if success:
        db[models.ORDERS].update_one({"_id": order["_id"]}, {"$set": {"status": models.OrderStatus.PAID}})

    # Fire webhook asynchronously (best-effort)
    merchant = db[models.MERCHANTS].find_one({"_id": ObjectId(order["merchant_id"])})
    if merchant and merchant.get("webhook_url"):
        try:
            from .webhooks import dispatch_webhook
            dispatch_webhook(
                merchant["_id"],
                "payment.captured" if success else "payment.failed",
                {
                    "payment_ref": payment["payment_ref"],
                    "order_ref": order_ref,
                    "amount": payment["amount"],
                    "method": payment["method"],
                    "status": payment["status"],
                },
            )
        except Exception:
            pass  # Never block checkout for webhook failures

    return serialize_doc(payment)


# ─── Hosted checkout HTML page ────────────────────────────────────────────────

@router.get(
    "/{order_ref}",
    response_class=HTMLResponse,
    summary="Hosted payment page",
)
def checkout_page(order_ref: str, db = Depends(get_db)):
    order = db[models.ORDERS].find_one({"order_ref": order_ref})
    if not order:
        return HTMLResponse("<h2>Order not found</h2>", status_code=404)

    merchant = db[models.MERCHANTS].find_one({"_id": ObjectId(order["merchant_id"])})
    business_name = merchant["business_name"] if merchant else "PayFlow Checkout"
    amount_rupees = order.get("amount", 0) / 100   # paise → ₹

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PayFlow Checkout — {business_name}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0a0a1a;
      --surface: #12122a;
      --surface2: #1a1a38;
      --border: rgba(99,102,241,0.25);
      --primary: #6366f1;
      --primary-glow: rgba(99,102,241,0.4);
      --success: #22c55e;
      --danger: #ef4444;
      --text: #f0f0ff;
      --muted: #8b8bb8;
      --card-shadow: 0 25px 60px rgba(0,0,0,0.6), 0 0 40px rgba(99,102,241,0.1);
    }}
    body {{
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background-image: radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.08) 0%, transparent 60%),
                        radial-gradient(ellipse at 80% 20%, rgba(139,92,246,0.05) 0%, transparent 50%);
    }}
    .checkout-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 24px;
      box-shadow: var(--card-shadow);
      width: 100%;
      max-width: 460px;
      overflow: hidden;
      animation: slideUp 0.4s ease;
    }}
    @keyframes slideUp {{
      from {{ opacity:0; transform: translateY(24px); }}
      to   {{ opacity:1; transform: translateY(0); }}
    }}
    .checkout-header {{
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      padding: 28px 32px;
      color: white;
    }}
    .merchant-name {{ font-size: 13px; opacity: 0.85; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }}
    .amount {{ font-size: 40px; font-weight: 700; margin-top: 6px; letter-spacing: -1px; }}
    .amount span {{ font-size: 22px; vertical-align: super; font-weight: 500; opacity: 0.85; }}
    .order-ref {{ font-size: 11px; opacity: 0.7; margin-top: 8px; font-family: monospace; }}
    .checkout-body {{ padding: 32px; }}
    .method-tabs {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 28px;
    }}
    .method-tab {{
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 6px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      color: var(--muted);
      font-size: 11px;
      font-weight: 500;
    }}
    .method-tab:hover {{ border-color: var(--primary); color: var(--text); }}
    .method-tab.active {{
      background: rgba(99,102,241,0.15);
      border-color: var(--primary);
      color: var(--primary);
      box-shadow: 0 0 12px var(--primary-glow);
    }}
    .method-tab .icon {{ font-size: 20px; margin-bottom: 4px; display: block; }}
    .form-section {{ display: none; }}
    .form-section.active {{ display: block; animation: fadeIn 0.25s ease; }}
    @keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
    .form-group {{ margin-bottom: 18px; }}
    label {{ display: block; font-size: 12px; color: var(--muted); font-weight: 500; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.04em; }}
    input {{
      width: 100%;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 16px;
      color: var(--text);
      font-size: 15px;
      font-family: 'Inter', sans-serif;
      transition: all 0.2s;
    }}
    input:focus {{
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }}
    input::placeholder {{ color: var(--muted); }}
    .card-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .pay-btn {{
      width: 100%;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border: none;
      border-radius: 12px;
      padding: 16px;
      color: white;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      margin-top: 8px;
      position: relative;
      overflow: hidden;
    }}
    .pay-btn:hover {{ transform: translateY(-1px); box-shadow: 0 8px 24px var(--primary-glow); }}
    .pay-btn:active {{ transform: translateY(0); }}
    .pay-btn:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; }}
    .secure-badge {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      margin-top: 18px;
      color: var(--muted);
      font-size: 12px;
    }}
    .result {{
      display: none;
      text-align: center;
      padding: 24px;
    }}
    .result.show {{ display: block; animation: fadeIn 0.3s ease; }}
    .result-icon {{ font-size: 56px; margin-bottom: 12px; }}
    .result h3 {{ font-size: 22px; font-weight: 600; color: var(--text); margin-bottom: 8px; }}
    .result p {{ color: var(--muted); font-size: 14px; margin-bottom: 4px; }}
    .result code {{ font-size: 11px; color: var(--primary); font-family: monospace; }}
    .spinner {{
      width: 20px; height: 20px;
      border: 2.5px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      display: inline-block;
      vertical-align: middle;
      margin-right: 8px;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>
  <div class="checkout-card">
    <div class="checkout-header">
      <div class="merchant-name">🏪 {business_name}</div>
      <div class="amount"><span>₹</span>{amount_rupees:,.2f}</div>
      <div class="order-ref">Order #{order_ref}</div>
    </div>

    <div class="checkout-body" id="checkoutBody">
      <div class="method-tabs">
        <div class="method-tab active" onclick="switchMethod('upi')" id="tab-upi">
          <span class="icon">📱</span>UPI
        </div>
        <div class="method-tab" onclick="switchMethod('card')" id="tab-card">
          <span class="icon">💳</span>Card
        </div>
        <div class="method-tab" onclick="switchMethod('netbanking')" id="tab-netbanking">
          <span class="icon">🏦</span>Net&nbsp;Banking
        </div>
        <div class="method-tab" onclick="switchMethod('wallet')" id="tab-wallet">
          <span class="icon">👛</span>Wallet
        </div>
      </div>

      <!-- UPI -->
      <div class="form-section active" id="form-upi">
        <div class="form-group">
          <label>UPI ID / VPA</label>
          <input type="text" id="vpa" placeholder="yourname@upi" autocomplete="off" />
        </div>
      </div>

      <!-- Card -->
      <div class="form-section" id="form-card">
        <div class="form-group">
          <label>Card Number</label>
          <input type="text" id="card_number" placeholder="1234 5678 9012 3456" maxlength="19" autocomplete="cc-number" />
        </div>
        <div class="form-group">
          <label>Name on Card</label>
          <input type="text" id="card_name" placeholder="John Doe" autocomplete="cc-name" />
        </div>
        <div class="card-row">
          <div class="form-group">
            <label>Expiry</label>
            <input type="text" id="card_expiry" placeholder="MM / YY" maxlength="7" autocomplete="cc-exp" />
          </div>
          <div class="form-group">
            <label>CVV</label>
            <input type="password" id="card_cvv" placeholder="•••" maxlength="4" autocomplete="cc-csc" />
          </div>
        </div>
      </div>

      <!-- Net Banking -->
      <div class="form-section" id="form-netbanking">
        <div class="form-group">
          <label>Your Email</label>
          <input type="email" id="nb_email" placeholder="you@bank.com" />
        </div>
        <div class="form-group">
          <label>Contact Number</label>
          <input type="tel" id="nb_contact" placeholder="+91 98765 43210" />
        </div>
      </div>

      <!-- Wallet -->
      <div class="form-section" id="form-wallet">
        <div class="form-group">
          <label>Wallet Linked Phone</label>
          <input type="tel" id="wallet_contact" placeholder="+91 98765 43210" />
        </div>
      </div>

      <button class="pay-btn" id="payBtn" onclick="submitPayment()">
        Pay ₹{amount_rupees:,.2f}
      </button>

      <div class="secure-badge">
        🔒 Secured by <strong style="color: var(--primary); margin-left:4px;">PayFlow</strong>
      </div>
    </div>

    <div class="result" id="resultSuccess">
      <div class="result-icon">✅</div>
      <h3>Payment Successful!</h3>
      <p>Your payment has been processed.</p>
      <p style="margin-top:8px">Payment ID: <code id="successRef"></code></p>
    </div>
    <div class="result" id="resultFailed">
      <div class="result-icon">❌</div>
      <h3>Payment Failed</h3>
      <p>Something went wrong. Please try again or use a different method.</p>
      <button class="pay-btn" onclick="resetForm()" style="margin-top:16px; max-width:200px; margin-inline:auto; display:block;">Try Again</button>
    </div>
  </div>

  <script>
    let activeMethod = 'upi';

    function switchMethod(method) {{
      document.querySelectorAll('.method-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.form-section').forEach(f => f.classList.remove('active'));
      document.getElementById('tab-' + method).classList.add('active');
      document.getElementById('form-' + method).classList.add('active');
      activeMethod = method;
    }}

    async function submitPayment() {{
      const btn = document.getElementById('payBtn');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span>Processing...';

      const body = {{
        order_ref: '{order_ref}',
        method: activeMethod,
        email: document.getElementById('nb_email')?.value || '',
        contact: document.getElementById('nb_contact')?.value || document.getElementById('wallet_contact')?.value || '',
        vpa: document.getElementById('vpa')?.value || '',
        card_number: document.getElementById('card_number')?.value || '',
        card_expiry: document.getElementById('card_expiry')?.value || '',
        card_cvv: document.getElementById('card_cvv')?.value || '',
        card_name: document.getElementById('card_name')?.value || '',
      }};

      try {{
        const resp = await fetch('/pay/{order_ref}', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(body),
        }});
        const data = await resp.json();

        document.getElementById('checkoutBody').style.display = 'none';

        if (data.status === 'captured') {{
          document.getElementById('successRef').textContent = data.payment_ref;
          document.getElementById('resultSuccess').classList.add('show');
        }} else {{
          document.getElementById('resultFailed').classList.add('show');
        }}
      }} catch (e) {{
        document.getElementById('checkoutBody').style.display = 'none';
        document.getElementById('resultFailed').classList.add('show');
      }}
    }}

    function resetForm() {{
      document.getElementById('checkoutBody').style.display = 'block';
      document.getElementById('resultFailed').classList.remove('show');
      document.getElementById('payBtn').disabled = false;
      document.getElementById('payBtn').innerHTML = 'Pay ₹{amount_rupees:,.2f}';
    }}

    // Card number formatting
    document.addEventListener('DOMContentLoaded', () => {{
      const cardInput = document.getElementById('card_number');
      if (cardInput) {{
        cardInput.addEventListener('input', e => {{
          let v = e.target.value.replace(/\\D/g,'').substring(0,16);
          e.target.value = v.replace(/(\\d{{4}})/g,'$1 ').trim();
        }});
      }}
      const expiryInput = document.getElementById('card_expiry');
      if (expiryInput) {{
        expiryInput.addEventListener('input', e => {{
          let v = e.target.value.replace(/\\D/g,'').substring(0,4);
          if (v.length >= 2) v = v.substring(0,2) + ' / ' + v.substring(2);
          e.target.value = v;
        }});
      }}
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(content=page)
