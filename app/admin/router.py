"""
/admin  — System-wide admin dashboard (MongoDB).
Only accessible by users with role = "admin".
Covers: legacy transactions + new gateway entities.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from datetime import datetime, timedelta
from collections import defaultdict

from ..database import get_db
from .. import models, schemas
from ..schemas import serialize_doc
from ..auth.router import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY TRANSACTIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/transactions", response_model=List[schemas.TransactionOut], summary="All legacy transactions")
def all_transactions(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cursor = db[models.TRANSACTIONS].find().sort("created_at", -1)
    return [serialize_doc(t) for t in cursor]


@router.get("/flagged", response_model=List[schemas.TransactionOut], summary="Flagged transactions")
def flagged_transactions(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cursor = db[models.TRANSACTIONS].find({"is_flagged": True}).sort("created_at", -1)
    return [serialize_doc(t) for t in cursor]


@router.get("/stats", response_model=schemas.TransactionStats, summary="Legacy transaction stats")
def transaction_stats(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    all_txns = list(db[models.TRANSACTIONS].find())
    return schemas.TransactionStats(
        total_transactions=len(all_txns),
        total_amount=sum(t.get("amount", 0) for t in all_txns),
        success_count=sum(1 for t in all_txns if t.get("status") == models.TransactionStatus.SUCCESS),
        failed_count=sum(1 for t in all_txns if t.get("status") == models.TransactionStatus.FAILED),
        flagged_count=sum(1 for t in all_txns if t.get("is_flagged", False)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/stats",
    response_model=schemas.GatewayStats,
    summary="Gateway-wide statistics",
    description="Total merchants, orders, payments, refunds and transaction volume across the whole platform.",
)
def gateway_stats(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    total_merchants = db[models.MERCHANTS].count_documents({})
    total_orders    = db[models.ORDERS].count_documents({})
    total_payments  = db[models.PAYMENTS].count_documents({})
    total_refunds   = db[models.REFUNDS].count_documents({})

    pipeline = [
        {"$match": {"status": models.PaymentStatus.CAPTURED}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    vol_aggr = list(db[models.PAYMENTS].aggregate(pipeline))
    total_volume = vol_aggr[0]["total"] if vol_aggr else 0

    return schemas.GatewayStats(
        total_merchants=total_merchants,
        total_orders=total_orders,
        total_payments=total_payments,
        total_volume_paise=total_volume,
        total_refunds=total_refunds,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — MERCHANTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/merchants",
    response_model=List[schemas.MerchantOut],
    summary="List all merchants",
)
def all_merchants(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cursor = db[models.MERCHANTS].find().sort("created_at", -1)
    return [serialize_doc(m) for m in cursor]


from bson import ObjectId

@router.patch(
    "/gateway/merchants/{merchant_id}/verify",
    response_model=schemas.MerchantOut,
    summary="Verify a merchant account",
)
def verify_merchant(
    merchant_id: str,
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        oid = ObjectId(merchant_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid merchant ID")

    merchant = db[models.MERCHANTS].find_one({"_id": oid})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    db[models.MERCHANTS].update_one({"_id": oid}, {"$set": {"is_verified": True}})
    merchant["is_verified"] = True
    return serialize_doc(merchant)


@router.patch(
    "/gateway/merchants/{merchant_id}/suspend",
    response_model=schemas.MerchantOut,
    summary="Suspend / deactivate a merchant",
)
def suspend_merchant(
    merchant_id: str,
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        oid = ObjectId(merchant_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid merchant ID")

    merchant = db[models.MERCHANTS].find_one({"_id": oid})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    db[models.MERCHANTS].update_one({"_id": oid}, {"$set": {"is_active": False}})
    merchant["is_active"] = False
    return serialize_doc(merchant)


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — PAYMENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/payments",
    response_model=List[schemas.PaymentOut],
    summary="All payments across all merchants",
)
def all_payments(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cursor = db[models.PAYMENTS].find().sort("created_at", -1).limit(200)
    return [serialize_doc(p) for p in cursor]


@router.get(
    "/gateway/payments/flagged",
    response_model=List[schemas.PaymentOut],
    summary="Flagged / suspicious payments",
)
def flagged_payments(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cursor = db[models.PAYMENTS].find({"is_flagged": True}).sort("created_at", -1)
    return [serialize_doc(p) for p in cursor]


# ─────────────────────────────────────────────────────────────────────────────
# GATEWAY — REFUNDS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gateway/refunds",
    response_model=List[schemas.RefundOut],
    summary="All refunds",
)
def all_refunds(
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cursor = db[models.REFUNDS].find().sort("created_at", -1).limit(200)
    return [serialize_doc(r) for r in cursor]


# ─────────────────────────────────────────────────────────────────────────────
# REVENUE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def _period_key(dt: datetime, period_type: str) -> str:
    """Convert a datetime to a bucket key string."""
    if not isinstance(dt, datetime):
        return ""
    if period_type == "daily":
        return dt.strftime("%Y-%m-%d")
    elif period_type == "weekly":
        return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
    else:  # monthly
        return dt.strftime("%Y-%m")


@router.get(
    "/revenue",
    response_model=schemas.RevenueDashboard,
    summary="Revenue dashboard — daily / weekly / monthly",
    description=(
        "Returns GMV, success rate, refund rate and net revenue "
        "bucketed by day, week, or month.\n\n"
        "**Query params:**\n"
        "- `period`: `daily` | `weekly` | `monthly` (default: daily)\n"
        "- `days`: look-back window in days (default: 30)"
    ),
)
def revenue_dashboard(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365),
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Fetch all payments + refunds in the window
    payments = list(db[models.PAYMENTS].find({"created_at": {"$gte": cutoff}}))
    refunds = list(db[models.REFUNDS].find({"created_at": {"$gte": cutoff}}))

    # Build per-period buckets
    buckets_data: dict[str, dict] = defaultdict(lambda: {
        "gmv": 0, "refunds": 0, "total": 0,
        "success": 0, "failed": 0, "refund_count": 0,
    })

    for p in payments:
        if "created_at" not in p: continue
        key = _period_key(p["created_at"], period)
        buckets_data[key]["total"] += 1
        if p.get("status") == models.PaymentStatus.CAPTURED:
            buckets_data[key]["gmv"] += p.get("amount", 0)
            buckets_data[key]["success"] += 1
        elif p.get("status") == models.PaymentStatus.FAILED:
            buckets_data[key]["failed"] += 1

    for r in refunds:
        if "created_at" not in r: continue
        key = _period_key(r["created_at"], period)
        buckets_data[key]["refunds"] += r.get("amount", 0)
        buckets_data[key]["refund_count"] += 1

    # Build sorted bucket list
    sorted_keys = sorted(buckets_data.keys())
    bucket_list = []
    grand_gmv = grand_refunds = grand_success = grand_total = grand_refund_count = 0

    for key in sorted_keys:
        d = buckets_data[key]
        net = d["gmv"] - d["refunds"]
        sr = d["success"] / d["total"] if d["total"] > 0 else 0.0
        rr = d["refund_count"] / d["total"] if d["total"] > 0 else 0.0

        bucket_list.append(schemas.RevenueBucket(
            period=key,
            total_gmv_paise=d["gmv"],
            total_refunds_paise=d["refunds"],
            net_revenue_paise=net,
            transaction_count=d["total"],
            success_count=d["success"],
            failed_count=d["failed"],
            refund_count=d["refund_count"],
            success_rate=round(sr, 4),
            refund_rate=round(rr, 4),
        ))

        grand_gmv += d["gmv"]
        grand_refunds += d["refunds"]
        grand_success += d["success"]
        grand_total += d["total"]
        grand_refund_count += d["refund_count"]

    return schemas.RevenueDashboard(
        period_type=period,
        buckets=bucket_list,
        total_gmv_paise=grand_gmv,
        total_refunds_paise=grand_refunds,
        total_net_paise=grand_gmv - grand_refunds,
        overall_success_rate=round(grand_success / grand_total, 4) if grand_total else 0.0,
        overall_refund_rate=round(grand_refund_count / grand_total, 4) if grand_total else 0.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAX / GST REPORT (India)
# ─────────────────────────────────────────────────────────────────────────────

GST_RATE = 0.18          # 18% total
CGST_RATE = GST_RATE / 2  # 9% Central
SGST_RATE = GST_RATE / 2  # 9% State


@router.get(
    "/gst-report",
    response_model=schemas.GSTReport,
    summary="GST / Tax report for Indian compliance",
    description=(
        "Monthly breakdown of gross revenue, refunds, net taxable amount, "
        "CGST (9%), SGST (9%), and total GST.\n\n"
        "**Query params:**\n"
        "- `fy`: Financial year start, e.g. `2025` for FY 2025-26 (April 2025 – March 2026)\n"
        "- If omitted, uses current FY."
    ),
)
def gst_report(
    fy: int = Query(None, description="FY start year, e.g. 2025 for FY 2025-26"),
    db = Depends(get_db),
    _: dict = Depends(require_admin),
):
    now = datetime.utcnow()
    if fy is None:
        fy = now.year if now.month >= 4 else now.year - 1
    fy_start = datetime(fy, 4, 1)
    fy_end = datetime(fy + 1, 3, 31, 23, 59, 59)
    fy_label = f"FY {fy}-{str(fy + 1)[-2:]}"

    # Fetch payments + refunds in the FY
    payments = list(db[models.PAYMENTS].find({
        "status": models.PaymentStatus.CAPTURED,
        "created_at": {"$gte": fy_start, "$lte": fy_end}
    }))
    refunds = list(db[models.REFUNDS].find({
        "created_at": {"$gte": fy_start, "$lte": fy_end}
    }))

    # Bucket by month
    monthly_gross: dict[str, int] = defaultdict(int)
    monthly_refunds: dict[str, int] = defaultdict(int)
    monthly_count: dict[str, int] = defaultdict(int)

    for p in payments:
        if "created_at" not in p: continue
        key = p["created_at"].strftime("%Y-%m")
        monthly_gross[key] += p.get("amount", 0)
        monthly_count[key] += 1

    for r in refunds:
        if "created_at" not in r: continue
        key = r["created_at"].strftime("%Y-%m")
        monthly_refunds[key] += r.get("amount", 0)

    # Generate all 12 months of the FY
    all_months = []
    for i in range(12):
        m = 4 + i
        y = fy if m <= 12 else fy + 1
        m = m if m <= 12 else m - 12
        all_months.append(f"{y}-{m:02d}")

    line_items = []
    total_gross = total_refunds = total_net = total_gst = 0

    for month in all_months:
        gross = monthly_gross.get(month, 0)
        ref = monthly_refunds.get(month, 0)
        net = gross - ref
        cgst = int(net * CGST_RATE)
        sgst = int(net * SGST_RATE)
        igst = cgst + sgst  # for inter-state (same total)
        gst_total = cgst + sgst

        line_items.append(schemas.GSTLineItem(
            month=month,
            gross_revenue_paise=gross,
            refunds_paise=ref,
            net_taxable_paise=net,
            cgst_paise=cgst,
            sgst_paise=sgst,
            igst_paise=igst,
            total_gst_paise=gst_total,
            total_with_gst_paise=net + gst_total,
            transaction_count=monthly_count.get(month, 0),
        ))

        total_gross += gross
        total_refunds += ref
        total_net += net
        total_gst += gst_total

    return schemas.GSTReport(
        financial_year=fy_label,
        gst_rate_percent=GST_RATE * 100,
        line_items=line_items,
        total_gross_paise=total_gross,
        total_refunds_paise=total_refunds,
        total_net_taxable_paise=total_net,
        total_gst_paise=total_gst,
    )
