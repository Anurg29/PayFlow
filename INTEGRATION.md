# 💳 PayFlow — Payment Gateway

PayFlow is a **self-hosted payment gateway** — think Razorpay, but one you own. Merchants integrate the REST API into their apps to accept UPI, card, net banking, and wallet payments.

---

## ⚡ Architecture Overview

```
Your App (merchant)          PayFlow Backend              End User
────────────────────         ─────────────────            ─────────
POST /v1/orders      ──▶    Creates Order                 
                            Returns order_ref             
                                                          
Redirect / SDK opens ──────────────────────────────▶   /pay/{order_ref}
                                                         User enters payment info
                                                         POST /pay/{order_ref}
                            Processes Payment ◀──────────
                            Fires Webhook     ──────────▶  Your webhook handler
POST /v1/payments/…  ──▶    Fetch/Capture/Refund
```

---

## 🚀 Quick Start (5 Steps)

### Step 1 — Register a merchant account
```bash
curl -X POST https://your-payflow.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@mystore.com","password":"secret","role":"merchant"}'
```

### Step 2 — Login to get your JWT
```bash
curl -X POST https://your-payflow.com/auth/login-json \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@mystore.com","password":"secret"}'
# Returns: { "access_token": "eyJ..." }
```

### Step 3 — Create your merchant profile
```bash
curl -X POST https://your-payflow.com/merchants/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Jane'\''s Store",
    "business_email": "payments@mystore.com",
    "website": "https://mystore.com",
    "webhook_url": "https://mystore.com/webhook/payflow"
  }'
```

### Step 4 — Generate your API keys
```bash
curl -X POST https://your-payflow.com/merchants/me/keys \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"label": "Production Key"}'

# Response (SAVE key_secret — shown only once!):
# {
#   "key_id": "pf_key_a1b2c3d4e5f6g7h8",
#   "key_secret": "pf_sec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
#   ...
# }
```

### Step 5 — Create an order & accept payment!
```bash
curl -X POST https://your-payflow.com/v1/orders \
  -u "pf_key_xxx:pf_sec_xxx" \
  -H "Content-Type: application/json" \
  -d '{"amount": 49900, "currency": "INR", "receipt": "order_1234"}'

# Returns: { "order_ref": "pf_order_xxxxxxxxxxxxxxxxxxxx", ... }
# Redirect your user to: https://your-payflow.com/pay/pf_order_xxxxxxxxxxxxxxxxxxxx
```

---

## 🛒 Embedding payflow.js (like Razorpay Checkout)

Drop this into your merchant website — no backend integration needed for the UI:

```html
<!DOCTYPE html>
<html>
<head><title>My Store Checkout</title></head>
<body>
  <button id="pay-btn">Pay ₹499</button>

  <!-- 1. Include the SDK -->
  <script src="https://your-payflow.com/static/payflow.js"></script>

  <script>
    // 2. Initialize with your key_id
    const pf = new PayFlow({ key: 'pf_key_yourkey' });

    document.getElementById('pay-btn').addEventListener('click', async () => {
      // 3. Create an order (via YOUR backend → POST /v1/orders)
      const res = await fetch('/api/create-order', { method: 'POST' });
      const order = await res.json();

      // 4. Open the PayFlow checkout modal
      pf.open({
        order_ref:   order.order_ref,
        amount:      49900,          // in paise (₹499.00)
        currency:    'INR',
        name:        'My Awesome Store',
        description: 'Premium plan - 1 month',
        prefill: {
          email:   'customer@example.com',
          contact: '9876543210',
        },
        theme: { color: '#6366f1' },

        // 5. Handle the result
        handler: function(response) {
          if (response.status === 'captured') {
            alert('Payment successful! ID: ' + response.payment_ref);
            // Verify on your backend: GET /v1/payments/{payment_ref}
          } else {
            alert('Payment failed. Please try again.');
          }
        },

        onDismiss: function() {
          console.log('User closed checkout');
        }
      });
    });
  </script>
</body>
</html>
```

---

## 🔌 REST API Reference

### Authentication
All `/v1/*` endpoints use **HTTP Basic Auth**:
```
Username: key_id   (e.g. pf_key_a1b2c3d4)
Password: key_secret (e.g. pf_sec_xxxx...)
```

### Orders API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/orders` | Create a new order |
| `GET`  | `/v1/orders` | List all your orders |
| `GET`  | `/v1/orders/{order_ref}` | Fetch a single order |
| `GET`  | `/v1/orders/{order_ref}/payments` | List payments for an order |

**Create Order Request:**
```json
{
  "amount": 49900,
  "currency": "INR",
  "receipt": "your_order_id_123",
  "notes": "{\"customer_id\": \"cust_456\"}"
}
```

**Amount is always in paise:** ₹1 = 100 paise, ₹499 = 49900 paise

### Payments API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/v1/payments/{payment_ref}` | Fetch payment details |
| `POST` | `/v1/payments/{payment_ref}/capture` | Capture authorized payment |
| `POST` | `/v1/payments/{payment_ref}/refund` | Issue full/partial refund |
| `GET`  | `/v1/payments/{payment_ref}/refunds` | List refunds for a payment |
| `GET`  | `/v1/webhooks/logs` | View webhook delivery logs |

**Issue Refund:**
```json
{
  "amount": 10000,
  "reason": "customer_request",
  "notes": "Order returned by customer"
}
```
Leave `amount` empty for a full refund.

---

## 🪝 Webhooks

PayFlow sends a **signed POST** to your `webhook_url` on payment events.

### Events
| Event | Trigger |
|-------|---------|
| `payment.captured` | Payment successfully captured |
| `payment.failed` | Payment attempt failed |
| `order.paid` | Order fully paid |
| `refund.processed` | Refund issued |

### Payload Structure
```json
{
  "event": "payment.captured",
  "created_at": "2026-02-24T07:13:00.000Z",
  "payload": {
    "payment_ref": "pf_pay_xxxx",
    "order_ref": "pf_order_xxxx",
    "amount": 49900,
    "method": "upi",
    "status": "captured"
  }
}
```

### Verifying the Signature
```python
import hmac, hashlib

def verify_payflow_webhook(payload_body: str, signature_header: str, secret: str) -> bool:
    expected = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload_body.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)

# In your FastAPI/Flask/Django app:
@app.post("/webhook/payflow")
async def handle_webhook(request: Request):
    body = await request.body()
    sig  = request.headers.get("X-PayFlow-Signature", "")
    
    if not verify_payflow_webhook(body.decode(), sig, "your-webhook-signing-secret"):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    data = await request.json()
    event = data["event"]
    
    if event == "payment.captured":
        order_ref = data["payload"]["order_ref"]
        # Fulfill the order
    
    return {"received": True}
```

### Node.js / Express
```javascript
const crypto = require('crypto');

app.post('/webhook/payflow', express.raw({ type: '*/*' }), (req, res) => {
  const sig = req.headers['x-payflow-signature'];
  const expected = crypto
    .createHmac('sha256', process.env.PAYFLOW_WEBHOOK_SECRET)
    .update(req.body)
    .digest('hex');

  if (sig !== expected) return res.status(401).send('Invalid signature');

  const event = JSON.parse(req.body);
  console.log('PayFlow event:', event.event);
  res.json({ received: true });
});
```

---

## 💰 Supported Payment Methods

| Method | Identifier | Details |
|--------|-----------|---------|
| UPI | `upi` | VPA (e.g. `user@upi`) |
| Debit/Credit Card | `card` | Visa, Mastercard, RuPay, Amex |
| Net Banking | `netbanking` | Email + Contact |
| Wallet | `wallet` | Phone-linked wallets |

---

## 🔐 Security

- **API Keys** — HMAC-signed `key_id:key_secret` pairs (bcrypt-hashed at rest)
- **Webhooks** — HMAC-SHA256 signed with your individual webhook secret
- **Fraud Detection** — 5 automated rules: high-value, duplicate, frequency, invalid VPA, velocity
- **Idempotency** — Built-in per the Orders model
- **JWT Auth** — For merchant dashboard and admin endpoints

---

## 🛠️ Running Locally

```bash
git clone https://github.com/yourname/payflow
cd payflow
cp .env.example .env            # Fill in SECRET_KEY
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** — full interactive Swagger UI.

---

## 📦 Project Structure

```
payflow/
├── app/
│   ├── main.py                  # FastAPI app, router wiring
│   ├── models.py                # SQLAlchemy models (User, Merchant, Order, Payment…)
│   ├── schemas.py               # Pydantic I/O schemas
│   ├── database.py              # DB engine + session
│   ├── auth/                    # JWT login/register
│   ├── gateway/
│   │   ├── router.py            # /v1 — Merchant REST API
│   │   ├── merchant_router.py   # /merchants — Onboarding + API keys
│   │   ├── checkout.py          # /pay — Hosted checkout page
│   │   ├── auth.py              # API key auth dependency
│   │   ├── keys.py              # Key generation + HMAC signing
│   │   ├── fraud.py             # Fraud detection engine
│   │   └── webhooks.py          # Webhook dispatcher
│   ├── admin/
│   │   └── router.py            # /admin — Gateway + txn stats
│   ├── transactions/            # Legacy user transaction API
│   └── static/
│       └── payflow.js           # Embeddable checkout SDK
├── requirements.txt
├── .env.example
└── INTEGRATION.md               # This file
```

---

## 🌐 Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Render (backend) + Firebase (frontend) setup.

**Key env vars for production:**
```bash
DATABASE_URL=postgresql://...
SECRET_KEY=<32-byte-random>
WEBHOOK_SIGNING_SECRET=<32-byte-random>
FRONTEND_URL=https://your-frontend.web.app
```
