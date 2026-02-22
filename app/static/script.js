const API_URL = ''; // Same origin

// ─── STATE MANAGEMENT ────────────────────────────────────────────────────────
let state = {
    token: localStorage.getItem('token'),
    user: null // Will decode from token or fetch profile
};

// Simple JWT decode (payload only)
function parseJwt(token) {
    try {
        return JSON.parse(atob(token.split('.')[1]));
    } catch (e) {
        return null;
    }
}

function init() {
    if (state.token) {
        const payload = parseJwt(state.token);
        if (payload && payload.exp * 1000 > Date.now()) {
            state.user = { email: payload.sub }; // We don't store full role in token, but we can guess or fetch. 
            // For this UI, we will rely on admin endpoints failing gracefully if not admin.
            // Let's reveal admin tabs aggressively for demo, or hide them. We can decode the role if we included it, but we didn't.
            // Let's show admin tabs and let the API reject with 403 if they click it.
            showAppView();
            return;
        }
    }
    showAuthView();
}

// ─── UTILS ───────────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'ri-information-line';
    if (type === 'success') icon = 'ri-checkbox-circle-line';
    if (type === 'error') icon = 'ri-error-warning-line';

    toast.innerHTML = `<i class="${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

const authHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${state.token}`
});

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);
}

// ─── UI NAVIGATION ───────────────────────────────────────────────────────────
function showAuthView() {
    document.getElementById('auth-view').classList.add('active');
    document.getElementById('app-view').classList.remove('active');
}

function showAppView() {
    document.getElementById('auth-view').classList.remove('active');
    document.getElementById('app-view').classList.add('active');
    
    document.getElementById('profile-name').innerText = state.user?.email.split('@')[0] || 'User';
    document.getElementById('profile-role').innerText = state.user?.email || '';

    // ALWAYS show admin tabs in UI for easy testing; non-admins get 403.
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');

    switchAppTab('dashboard');
}

function switchAuthTab(tab) {
    document.querySelectorAll('.auth-tabs .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
    
    if (tab === 'login') {
        document.querySelector('.auth-tabs .tab:nth-child(1)').classList.add('active');
        document.getElementById('login-form').classList.add('active');
    } else {
        document.querySelector('.auth-tabs .tab:nth-child(2)').classList.add('active');
        document.getElementById('register-form').classList.add('active');
    }
}

function switchAppTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    event?.currentTarget?.classList?.add('active');
    
    document.querySelectorAll('.app-tab').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabId}`).classList.add('active');

    const titles = {
        'dashboard': 'My Dashboard',
        'admin-stats': 'System Statistics',
        'admin-flagged': 'Flagged Transactions'
    };
    document.getElementById('page-title').innerText = titles[tabId];

    if (tabId === 'dashboard') fetchTransactions();
    if (tabId === 'admin-stats') fetchAdminStats();
    if (tabId === 'admin-flagged') fetchAdminFlagged();
}

function logout() {
    localStorage.removeItem('token');
    state.token = null;
    state.user = null;
    showToast('Logged out successfully', 'success');
    showAuthView();
}

// ─── API HANDLERS ────────────────────────────────────────────────────────────

// Register
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('reg-btn');
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i>';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: document.getElementById('reg-name').value,
                email: document.getElementById('reg-email').value,
                password: document.getElementById('reg-password').value,
                role: document.getElementById('reg-role').value
            })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed');
        
        showToast('Account created! Please login.', 'success');
        switchAuthTab('login');
        
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.innerHTML = '<span>Create Account</span><i class="ri-arrow-right-line"></i>';
        btn.disabled = false;
    }
});

// Login
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i>';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_URL}/auth/login-json`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: document.getElementById('login-email').value,
                password: document.getElementById('login-password').value
            })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Login failed');
        
        localStorage.setItem('token', data.access_token);
        state.token = data.access_token;
        init();
        showToast('Welcome back!', 'success');
        
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.innerHTML = '<span>Sign In</span><i class="ri-arrow-right-line"></i>';
        btn.disabled = false;
    }
});

// Create Payment
document.getElementById('payment-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('pay-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i> Processing...';
    btn.disabled = true;

    try {
        const amount = parseFloat(document.getElementById('pay-amount').value);
        const method = document.querySelector('input[name="method"]:checked').value;
        const idemKey = 'txn-' + Date.now() + '-' + Math.random().toString(36).substr(2, 5);

        const res = await fetch(`${API_URL}/transactions/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
                amount: amount,
                payment_method: method,
                idempotency_key: idemKey
            })
        });
        
        const data = await res.json();
        if (!res.ok) {
            if (res.status === 401) logout();
            throw new Error(data.detail || 'Payment failed');
        }
        
        if (data.is_flagged) {
            showToast('Warning: Transaction flagged for anomaly detection limit!', 'error');
        } else if (data.status === 'success') {
            showToast(`₹${amount} paid successfully via ${method.toUpperCase()}`, 'success');
        } else {
            showToast(`Transaction ${data.status}`, 'error');
        }
        
        document.getElementById('pay-amount').value = '';
        fetchTransactions();
        
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

// Fetch Transactions
async function fetchTransactions() {
    try {
        const res = await fetch(`${API_URL}/transactions/`, { headers: authHeaders() });
        if (res.status === 401) return logout();
        if (!res.ok) throw new Error('Failed to fetch txns');
        
        const txns = await res.json();
        renderTransactionList(txns, 'transactions-list');
        
        // Update dashboard stats
        const total = txns.reduce((sum, t) => sum + (t.status === 'success' ? t.amount : 0), 0);
        document.getElementById('total-amount').innerText = formatCurrency(total);
        document.getElementById('total-count').innerText = `${txns.length} total transactions`;

    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Fetch Admin Stats
async function fetchAdminStats() {
    try {
        const res = await fetch(`${API_URL}/admin/stats`, { headers: authHeaders() });
        if (res.status === 403) {
            document.getElementById('tab-admin-stats').innerHTML = '<div class="empty-state">Admin access required.</div>';
            return;
        }
        if (!res.ok) throw new Error('Stats fetch failed');
        
        const stats = await res.json();
        document.getElementById('admin-total-vol').innerText = formatCurrency(stats.total_amount);
        document.getElementById('admin-success-rate').innerText = 
            stats.total_transactions > 0 
                ? Math.round((stats.success_count / stats.total_transactions) * 100) + '%' 
                : '0%';
        document.getElementById('admin-flagged-count').innerText = stats.flagged_count;
        document.getElementById('admin-failed-count').innerText = stats.failed_count;
        
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Fetch Admin Flagged
async function fetchAdminFlagged() {
    try {
        const res = await fetch(`${API_URL}/admin/flagged`, { headers: authHeaders() });
        if (res.status === 403) {
            document.getElementById('flagged-list').innerHTML = '<div class="empty-state">Admin access required.</div>';
            return;
        }
        if (!res.ok) throw new Error('Fetch failed');
        
        const txns = await res.json();
        renderTransactionList(txns, 'flagged-list');
        
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Refunding
async function refundTransaction(id) {
    if (!confirm('Are you sure you want to refund this transaction?')) return;
    try {
        const res = await fetch(`${API_URL}/transactions/${id}/refund`, {
            method: 'POST',
            headers: authHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Refund failed');
        showToast('Refund successful', 'success');
        fetchTransactions(); // refresh
    } catch (err) {
        showToast(err.message, 'error');
    }
}


function renderTransactionList(txns, containerId) {
    const list = document.getElementById(containerId);
    if (!txns || txns.length === 0) {
        list.innerHTML = `<div class="empty-state">No transactions found.</div>`;
        return;
    }

    const methodIcons = {
        'upi': 'ri-qr-code-line',
        'card': 'ri-bank-card-line',
        'netbanking': 'ri-bank-line'
    };

    list.innerHTML = txns.map(t => {
        const icon = methodIcons[t.payment_method] || 'ri-money-dollar-circle-line';
        const date = new Date(t.created_at).toLocaleString();
        const flagBadge = t.is_flagged ? `<span class="badge-flagged"><i class="ri-alert-line"></i> FLAGGED</span>` : '';
        
        let actions = '';
        if (t.status === 'success') {
            actions = `<button onclick="refundTransaction(${t.id})" class="btn-outline" style="font-size: 0.7rem; padding: 0.2rem 0.5rem; margin-top: 5px;">Refund</button>`;
        }

        return `
            <div class="txn-item">
                <div class="txn-left">
                    <div class="txn-icon"><i class="${icon}"></i></div>
                    <div class="txn-details">
                        <h4>${t.idempotency_key} ${flagBadge}</h4>
                        <div class="status-badge status-${t.status}">
                            ${t.status === 'success' ? '<i class="ri-check-line"></i>' : ''}
                            ${t.status}
                        </div>
                        <p>${date} • ${t.payment_method}</p>
                    </div>
                </div>
                <div class="txn-right">
                    <div class="txn-amount ${t.status === 'success' ? 'text-green' : (t.status === 'failed' ? 'text-red' : '')}">
                        ${t.status === 'refunded' ? '-' : ''}${formatCurrency(t.amount)}
                    </div>
                    ${actions}
                </div>
            </div>
        `;
    }).join('');
}

// Run init
init();
