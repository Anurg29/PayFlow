"""
Redis-backed distributed cache for fast transaction lookups.
Falls back to in-memory dict if Redis is unavailable.
"""

import os
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TTL = 300  # 5 minutes

try:
    _r = redis.from_url(REDIS_URL, decode_responses=True)
    _r.ping()
    _use_redis = True
except Exception:
    _r = None
    _use_redis = False
    _fallback: dict[int, dict] = {}


def get_cached_transaction(txn_id) -> dict | None:
    key = f"txn:{txn_id}"
    if _use_redis:
        data = _r.get(key)
        return json.loads(data) if data else None
    return _fallback.get(str(txn_id))


def set_cached_transaction(txn_id, data: dict, ttl: int = TTL):
    key = f"txn:{txn_id}"
    if _use_redis:
        _r.setex(key, ttl, json.dumps(data, default=str))
    else:
        _fallback[str(txn_id)] = data


def invalidate_transaction(txn_id):
    key = f"txn:{txn_id}"
    if _use_redis:
        _r.delete(key)
    else:
        _fallback.pop(str(txn_id), None)


def clear_cache():
    if _use_redis:
        for key in _r.scan_iter("txn:*"):
            _r.delete(key)
    else:
        _fallback.clear()
