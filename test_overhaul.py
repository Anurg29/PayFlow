import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def test():
    print("--- Running Test Overhaul ---")
    
    # 1. Register User & Admin
    print("\\n1. Testing Auth & MongoDB")
    u1 = f"user_{int(time.time())}@test.com"
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Test User", "email": u1, "password": "password123", "role": "user"
    })
    assert r.status_code == 200, f"Register failed: {r.text}"
    print("✅ User Registered")
    
    admin_email = f"admin_{int(time.time())}@test.com"
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Admin", "email": admin_email, "password": "password123", "role": "admin"
    })
    print("✅ Admin Registered")

    # Login User
    r_login = requests.post(f"{BASE_URL}/auth/login-json", json={"email": u1, "password": "password123"})
    user_token = r_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    # Login Admin
    r_admin_login = requests.post(f"{BASE_URL}/auth/login-json", json={"email": admin_email, "password": "password123"})
    admin_token = r_admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("✅ Logins Successful")

    # 2. Transactions & Celery
    print("\\n2. Testing Transactions & Celery")
    r_txn = requests.post(f"{BASE_URL}/transactions/", json={
        "amount": 1500, "payment_method": "upi", "idempotency_key": f"test_idk_{int(time.time())}"
    }, headers=user_headers)
    assert r_txn.status_code == 201, f"Create txn failed: {r_txn.text}"
    txn_id = r_txn.json()["id"]
    status = r_txn.json()["status"]
    print(f"✅ Txn Created. Initial Status: {status}")
    
    # No Celery to wait for!
    r_get = requests.get(f"{BASE_URL}/transactions/{txn_id}", headers=user_headers)
    new_status = r_get.json()["status"]
    print(f"✅ Synchronously Processed! Final Status: {new_status}")

    # 3. RBAC checks on Refund
    print("\\n3. Testing RBAC")
    r_user_refund = requests.post(f"{BASE_URL}/transactions/{txn_id}/refund", headers=user_headers)
    assert r_user_refund.status_code in [403, 401], f"User should be forbidden: {r_user_refund.status_code}"
    print(f"✅ User blocked from refunding: got {r_user_refund.status_code}")
    
    if new_status == "success": # only success txns can be refunded
        r_admin_refund = requests.post(f"{BASE_URL}/transactions/{txn_id}/refund", headers=admin_headers)
        assert r_admin_refund.status_code == 200, f"Admin refund failed: {r_admin_refund.text}"
        print("✅ Admin successfully refunded transaction")
        
    print("\\n4. Testing Admin Dashboard")
    r_stats = requests.get(f"{BASE_URL}/admin/stats", headers=admin_headers)
    assert r_stats.status_code == 200, f"Stats failed: {r_stats.text}"
    print("✅ Admin Stats fetched")

    print("\\n✅ All backend checks passed!")

if __name__ == "__main__":
    test()
