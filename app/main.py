"""
PayFlow — Main application entry point.

Run with:  uvicorn app.main:app --reload

Architecture:
  /auth        — JWT login/register (all users)
  /merchants   — Merchant onboarding + API key management (JWT)
  /v1          — Gateway REST API for merchant integrations (API key auth)
  /pay         — Hosted checkout page & payment submission (public)
  /transactions — Legacy user-scoped transactions (JWT)
  /admin       — Admin dashboard (JWT + admin role)
  /docs        — Interactive Swagger UI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .auth.router import router as auth_router
from .transactions.router import router as transactions_router
from .admin.router import router as admin_router
from .gateway.router import router as gateway_router
from .gateway.merchant_router import router as merchant_router
from .gateway.checkout import router as checkout_router

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="💳 PayFlow — Payment Gateway API",
    description=(
        "**PayFlow is a complete payment gateway** — use it like Razorpay.\n\n"
        "## Quick Start for Developers\n"
        "1. `POST /auth/register` with `role: merchant`\n"
        "2. `POST /auth/login` to get your JWT token\n"
        "3. `POST /merchants/` to register your business\n"
        "4. `POST /merchants/me/keys` to generate `key_id` + `key_secret`\n"
        "5. Use `key_id:key_secret` as HTTP Basic Auth for all `/v1/*` endpoints\n"
        "6. `POST /v1/orders` → create an order → redirect user to `/pay/{order_ref}`\n\n"
        "## Webhook Verification\n"
        "All webhook POSTs include `X-PayFlow-Signature` (HMAC-SHA256) for verification.\n\n"
        "## Supported Payment Methods\n"
        "UPI · Card (Visa/MC/RuPay/Amex) · Net Banking · Wallet"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "PayFlow Support", "email": "support@payflow.app"},
    license_info={"name": "MIT"},
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

_frontend_url = os.getenv("FRONTEND_URL", "")
_allowed_origins = (
    [_frontend_url, "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    if _frontend_url
    else ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router)           # /auth
app.include_router(merchant_router)       # /merchants
app.include_router(gateway_router)        # /v1  (API key auth)
app.include_router(checkout_router)       # /pay (public)
app.include_router(transactions_router)   # /transactions (legacy)
app.include_router(admin_router)          # /admin

# ─── Static / Frontend ────────────────────────────────────────────────────────

os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", tags=["home"], response_class=HTMLResponse)
def serve_home():
    """Landing page / frontend."""
    static_index = "app/static/index.html"
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return HTMLResponse("""
    <html><head><title>PayFlow</title></head><body style="font-family:sans-serif;padding:40px">
    <h1>💳 PayFlow Gateway</h1>
    <p>The backend is running. Visit <a href="/docs">/docs</a> for the interactive API reference.</p>
    </body></html>
    """)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "version": "2.0.0", "service": "PayFlow Gateway"}
