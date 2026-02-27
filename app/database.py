"""
PayFlow — MongoDB Database Connection.

Supports MongoDB Atlas (production) and local MongoDB (dev).
Set MONGODB_URL in .env:
  Atlas:  mongodb+srv://user:pass@cluster.mongodb.net/
  Local:  mongodb://localhost:27017
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    MONGODB_URL = "mongodb://localhost:27017"
    
MONGODB_DB = os.getenv("MONGODB_DB")
if not MONGODB_DB:
    MONGODB_DB = "payflow"

# ── Sync client (used by FastAPI sync endpoints) ──────────────────────────────
client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[MONGODB_DB]


def get_db():
    """FastAPI dependency — returns the MongoDB database object."""
    return db
