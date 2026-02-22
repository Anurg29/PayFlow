"""
Simple in-memory cache for fast transaction lookups.
Reduces DB queries for frequently accessed transactions.
"""

from typing import Optional, Dict

_cache: Dict[int, dict] = {}


def get_cached_transaction(txn_id: int) -> Optional[dict]:
    return _cache.get(txn_id)


def set_cached_transaction(txn_id: int, data: dict):
    _cache[txn_id] = data


def invalidate_transaction(txn_id: int):
    _cache.pop(txn_id, None)


def clear_cache():
    _cache.clear()
