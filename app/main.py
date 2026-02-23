"""
PayFlow — main application entry point.
Run with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .auth.router import router as auth_router
from .transactions.router import router as transactions_router
from .admin.router import router as admin_router

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PayFlow — Real-Time Payment Transaction API 💳",
    description=(
        "A fintech-grade payment backend built with FastAPI.\n\n"
        "Features: Transaction State Machine · Multi-method Payment Routing · "
        "Anomaly Detection · Idempotency Keys · In-Memory Caching · JWT Auth (Admin/Merchant/User)"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# In production, only allow requests from the Firebase frontend URL.
# Set FRONTEND_URL env var on Render to your Firebase URL e.g. https://payflow-xxx.web.app
# In development (no FRONTEND_URL set), we allow localhost origins.
_frontend_url = os.getenv("FRONTEND_URL", "")
_allowed_origins = (
    [_frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"]
    if _frontend_url
    else ["http://localhost:5173", "http://127.0.0.1:5173"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(admin_router)

# Create static directory if it doesn't exist
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", tags=["frontend"])
def serve_frontend():
    return FileResponse("app/static/index.html")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
