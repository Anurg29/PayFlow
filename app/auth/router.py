"""
/auth — Register, Login, Change Password (MongoDB).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import os
import datetime

from ..database import get_db
from .. import models, schemas
from .utils import get_password_hash, verify_password, create_access_token
from ..schemas import serialize_doc

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ── Register ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db=Depends(get_db)):
    role = user.role or "user"
    col_name = "users"
    if role == "admin":
        col_name = "admins"
    elif role == "merchant":
        col_name = "merchant_users"

    existing = db[col_name].find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    doc = {
        "name": user.name,
        "email": user.email,
        "hashed_password": get_password_hash(user.password),
        "role": role,
        "created_at": datetime.datetime.utcnow(),
    }
    result = db[col_name].insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


def _find_user_by_email(db, email: str):
    for col in ["users", "admins", "merchant_users"]:
        user = db[col].find_one({"email": email})
        if user:
            return user, col
    return None, None

# ── Login (form-encoded — for Swagger UI) ─────────────────────────────────────
@router.post("/login", response_model=schemas.Token)
def login(creds: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user, _ = _find_user_by_email(db, creds.username)
    if not user or not verify_password(creds.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user["email"], "role": user.get("role", "user")})
    return {"access_token": token, "token_type": "bearer"}


# ── Login (JSON — for frontend / curl) ────────────────────────────────────────
@router.post("/login-json", response_model=schemas.Token)
def login_json(data: dict, db=Depends(get_db)):
    email = data.get("email")
    password = data.get("password")
    
    user, _ = _find_user_by_email(db, email)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user["email"], "role": user.get("role", "user")})
    return {"access_token": token, "token_type": "bearer"}


# ── Get Current User (dependency) ─────────────────────────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    cred_exc = HTTPException(
        status_code=401, detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            os.getenv("SECRET_KEY", "your-secret-key"),
            algorithms=[os.getenv("ALGORITHM", "HS256")],
        )
        email: str = payload.get("sub")
        if email is None:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user, _ = _find_user_by_email(db, email)
    if user is None:
        raise cred_exc
    return serialize_doc(user)


# ── Change Password ───────────────────────────────────────────────────────────
@router.post("/change-password", summary="Change current user password")
def change_password(data: dict, db=Depends(get_db), current_user=Depends(get_current_user)):
    current_pw = data.get("current_password")
    new_pw = data.get("new_password")

    if not current_pw or not new_pw:
        raise HTTPException(status_code=400, detail="Both current_password and new_password are required")

    # Re-fetch to get hashed_password (serialize_doc strips it)
    user_doc, col = _find_user_by_email(db, current_user["email"])
    if not user_doc or not verify_password(current_pw, user_doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if len(new_pw) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    db[col].update_one(
        {"email": current_user["email"]},
        {"$set": {"hashed_password": get_password_hash(new_pw)}},
    )
    return {"message": "Password updated successfully"}
