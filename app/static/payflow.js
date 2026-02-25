/**
 * PayFlow.js — Embeddable Payment Checkout SDK
 * Version: 2.0.0
 *
 * Usage:
 *   <script src="https://your-payflow-api.com/static/payflow.js"></script>
 *   <script>
 *     const pf = new PayFlow({ key: 'pf_key_xxx' });
 *     pf.open({
 *       order_ref: 'pf_order_xxx',
 *       amount: 49900,           // in paise
 *       currency: 'INR',
 *       name: 'My Store',
 *       description: 'Order #1234',
 *       prefill: { email: 'user@example.com', contact: '9876543210' },
 *       theme: { color: '#6366f1' },
 *       handler: function(response) {
 *         // response.payment_ref, response.order_ref, response.status
 *         console.log('Payment done:', response);
 *       }
 *     });
 *   </script>
 */

(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined'
        ? (module.exports = factory())
        : typeof define === 'function' && define.amd
            ? define(factory)
            : (global.PayFlow = factory());
})(this, function () {
    'use strict';

    const BASE_URL = (function () {
        const scripts = document.querySelectorAll('script[src*="payflow.js"]');
        if (scripts.length) {
            const src = scripts[scripts.length - 1].src;
            const url = new URL(src);
            return url.origin;
        }
        return window.location.origin;
    })();

    const STYLES = `
    .pf-overlay {
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(6px);
      display: flex; align-items: center; justify-content: center;
      padding: 16px;
      opacity: 0; transition: opacity 0.25s ease;
    }
    .pf-overlay.pf-visible { opacity: 1; }
    .pf-modal {
      background: #12122a;
      border: 1px solid rgba(99,102,241,0.3);
      border-radius: 20px;
      width: 100%; max-width: 420px;
      box-shadow: 0 30px 80px rgba(0,0,0,0.7), 0 0 40px rgba(99,102,241,0.15);
      overflow: hidden;
      transform: translateY(20px) scale(0.97);
      transition: transform 0.3s ease, opacity 0.3s ease;
      font-family: -apple-system, 'Inter', BlinkMacSystemFont, sans-serif;
    }
    .pf-overlay.pf-visible .pf-modal {
      transform: translateY(0) scale(1);
    }
    .pf-header {
      padding: 22px 24px 18px;
      border-bottom: 1px solid rgba(99,102,241,0.15);
      display: flex; align-items: center; justify-content: space-between;
    }
    .pf-brand { display:flex; align-items:center; gap:10px; }
    .pf-logo {
      width: 36px; height: 36px; border-radius: 10px;
      background: linear-gradient(135deg,#6366f1,#8b5cf6);
      display:flex; align-items:center; justify-content:center;
      font-size:18px; color:white;
    }
    .pf-merchant-name { font-size:15px; font-weight:600; color:#f0f0ff; }
    .pf-amount-badge {
      font-size: 13px; font-weight: 600; color: white;
      background: linear-gradient(135deg,#6366f1,#8b5cf6);
      border-radius: 8px; padding: 5px 12px;
    }
    .pf-close {
      background: none; border: none; cursor: pointer;
      color: #8b8bb8; font-size: 20px; line-height:1;
      margin-left: 12px; padding: 4px;
      transition: color 0.2s;
    }
    .pf-close:hover { color: #f0f0ff; }
    .pf-body { padding: 22px 24px 28px; }
    .pf-desc { font-size: 13px; color: #8b8bb8; margin-bottom: 20px; }
    .pf-methods { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:22px; }
    .pf-method {
      background: #1a1a38; border: 1px solid rgba(99,102,241,0.2);
      border-radius: 10px; padding: 10px 4px;
      cursor: pointer; text-align: center;
      color: #8b8bb8; font-size: 10px; font-weight: 500;
      transition: all 0.2s;
    }
    .pf-method:hover { border-color: #6366f1; color: #f0f0ff; }
    .pf-method.active {
      background: rgba(99,102,241,0.15);
      border-color: #6366f1; color: #6366f1;
      box-shadow: 0 0 10px rgba(99,102,241,0.3);
    }
    .pf-method-icon { font-size:18px; display:block; margin-bottom:3px; }
    .pf-section { display:none; }
    .pf-section.active { display:block; animation: pfFadeIn 0.2s ease; }
    @keyframes pfFadeIn { from{opacity:0} to{opacity:1} }
    .pf-group { margin-bottom: 14px; }
    .pf-label {
      display:block; font-size:11px; font-weight:500;
      color:#8b8bb8; margin-bottom:5px;
      text-transform:uppercase; letter-spacing:0.04em;
    }
    .pf-input {
      width:100%; background:#1a1a38;
      border: 1px solid rgba(99,102,241,0.2);
      border-radius:9px; padding:11px 14px;
      color:#f0f0ff; font-size:14px;
      font-family: inherit;
      transition: all 0.2s; box-sizing:border-box;
    }
    .pf-input:focus {
      outline:none; border-color:#6366f1;
      box-shadow: 0 0 0 3px rgba(99,102,241,0.25);
    }
    .pf-input::placeholder { color:#8b8bb8; }
    .pf-row { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
    .pf-btn {
      width:100%; padding:14px; border:none; border-radius:11px;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      color:white; font-size:15px; font-weight:600;
      cursor:pointer; transition: all 0.2s; margin-top:6px;
    }
    .pf-btn:hover { transform:translateY(-1px); box-shadow:0 8px 24px rgba(99,102,241,0.4); }
    .pf-btn:disabled { opacity:0.55; cursor:not-allowed; transform:none; }
    .pf-secure {
      text-align:center; font-size:11px; color:#8b8bb8;
      margin-top:14px; display:flex; align-items:center;
      justify-content:center; gap:5px;
    }
    .pf-secure a { color:#6366f1; text-decoration:none; font-weight:500; }
    .pf-spinner {
      width:16px; height:16px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color:white; border-radius:50%;
      animation: pfSpin 0.7s linear infinite;
      display:inline-block; vertical-align:middle; margin-right:7px;
    }
    @keyframes pfSpin { to{transform:rotate(360deg)} }
    .pf-result { text-align:center; padding:28px 10px; display:none; }
    .pf-result.pf-show { display:block; animation:pfFadeIn 0.3s ease; }
    .pf-result-icon { font-size:52px; margin-bottom:10px; }
    .pf-result h3 { font-size:20px; font-weight:600; color:#f0f0ff; margin-bottom:6px; }
    .pf-result p { color:#8b8bb8; font-size:13px; }
    .pf-result code { color:#6366f1; font-size:11px; font-family:monospace; }
    .pf-retry {
      margin-top:16px; padding:10px 28px; border:1px solid rgba(99,102,241,0.4);
      border-radius:9px; background:none; color:#6366f1;
      cursor:pointer; font-size:13px; font-weight:500;
      transition:all 0.2s;
    }
    .pf-retry:hover { background:rgba(99,102,241,0.1); }
  `;

    function injectStyles() {
        if (document.getElementById('pf-styles')) return;
        const s = document.createElement('style');
        s.id = 'pf-styles';
        s.textContent = STYLES;
        document.head.appendChild(s);
    }

    function formatINR(paise) {
        const rupees = paise / 100;
        return '₹' + rupees.toLocaleString('en-IN', { minimumFractionDigits: 2 });
    }

    function buildModal(opts) {
        const o = opts || {};
        const name = o.name || 'Merchant';
        const amount = o.amount || 0;
        const desc = o.description || '';
        const color = (o.theme && o.theme.color) || '#6366f1';
        const email = (o.prefill && o.prefill.email) || '';
        const contact = (o.prefill && o.prefill.contact) || '';

        const overlay = document.createElement('div');
        overlay.className = 'pf-overlay';
        overlay.id = 'pf-overlay-' + Date.now();
        overlay.innerHTML = `
      <div class="pf-modal" id="pf-modal">
        <div class="pf-header">
          <div class="pf-brand">
            <div class="pf-logo">💳</div>
            <div>
              <div class="pf-merchant-name">${name}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:6px">
            <div class="pf-amount-badge">${formatINR(amount)}</div>
            <button class="pf-close" id="pf-close-btn">✕</button>
          </div>
        </div>
        <div class="pf-body" id="pf-form-area">
          ${desc ? `<div class="pf-desc">${desc}</div>` : ''}
          <div class="pf-methods">
            <div class="pf-method active" data-method="upi">
              <span class="pf-method-icon">📱</span>UPI
            </div>
            <div class="pf-method" data-method="card">
              <span class="pf-method-icon">💳</span>Card
            </div>
            <div class="pf-method" data-method="netbanking">
              <span class="pf-method-icon">🏦</span>Net&nbsp;Bank
            </div>
            <div class="pf-method" data-method="wallet">
              <span class="pf-method-icon">👛</span>Wallet
            </div>
          </div>

          <div class="pf-section active" id="pf-sec-upi">
            <div class="pf-group">
              <label class="pf-label">UPI ID / VPA</label>
              <input class="pf-input" id="pf-vpa" placeholder="yourname@upi" value="" />
            </div>
          </div>

          <div class="pf-section" id="pf-sec-card">
            <div class="pf-group">
              <label class="pf-label">Card Number</label>
              <input class="pf-input" id="pf-card-num" placeholder="1234 5678 9012 3456" maxlength="19" />
            </div>
            <div class="pf-group">
              <label class="pf-label">Name on Card</label>
              <input class="pf-input" id="pf-card-name" placeholder="John Doe" />
            </div>
            <div class="pf-row">
              <div class="pf-group">
                <label class="pf-label">Expiry</label>
                <input class="pf-input" id="pf-card-exp" placeholder="MM / YY" maxlength="7" />
              </div>
              <div class="pf-group">
                <label class="pf-label">CVV</label>
                <input class="pf-input" id="pf-card-cvv" type="password" placeholder="•••" maxlength="4" />
              </div>
            </div>
          </div>

          <div class="pf-section" id="pf-sec-netbanking">
            <div class="pf-group">
              <label class="pf-label">Email</label>
              <input class="pf-input" id="pf-nb-email" placeholder="you@email.com" value="${email}" />
            </div>
            <div class="pf-group">
              <label class="pf-label">Contact</label>
              <input class="pf-input" id="pf-nb-contact" placeholder="+91 98765 43210" value="${contact}" />
            </div>
          </div>

          <div class="pf-section" id="pf-sec-wallet">
            <div class="pf-group">
              <label class="pf-label">Linked Phone Number</label>
              <input class="pf-input" id="pf-wallet-phone" placeholder="+91 98765 43210" value="${contact}" />
            </div>
          </div>

          <button class="pf-btn" id="pf-pay-btn">Pay ${formatINR(amount)}</button>
          <div class="pf-secure">
            🔒 Secured by <a href="#" target="_blank">PayFlow</a>
          </div>
        </div>

        <div class="pf-result" id="pf-result-ok">
          <div class="pf-result-icon">✅</div>
          <h3>Payment Successful!</h3>
          <p style="margin-top:6px">Payment ID: <code id="pf-ok-ref"></code></p>
        </div>
        <div class="pf-result" id="pf-result-fail">
          <div class="pf-result-icon">❌</div>
          <h3>Payment Failed</h3>
          <p>Please try a different payment method.</p>
          <button class="pf-retry" id="pf-retry-btn">Try Again</button>
        </div>
      </div>`;
        return overlay;
    }

    // ────────────────────────────────────────────────────────────────────────────

    function PayFlow(config) {
        if (!config || !config.key) throw new Error('PayFlow: key is required');
        this._key = config.key;
        this._baseUrl = config.baseUrl || BASE_URL;
        this._overlay = null;
        this._activeMethod = 'upi';
        this._opts = null;
    }

    PayFlow.prototype.open = function (opts) {
        injectStyles();
        this._opts = opts || {};

        const overlay = buildModal(opts);
        this._overlay = overlay;
        document.body.appendChild(overlay);

        // Animate in
        requestAnimationFrame(() => overlay.classList.add('pf-visible'));

        // Wire up events
        this._wire();
    };

    PayFlow.prototype._wire = function () {
        const me = this;
        const overlay = this._overlay;

        // Close
        overlay.querySelector('#pf-close-btn').addEventListener('click', () => me.close());
        overlay.addEventListener('click', (e) => { if (e.target === overlay) me.close(); });

        // Method tabs
        overlay.querySelectorAll('.pf-method').forEach((tab) => {
            tab.addEventListener('click', () => {
                const method = tab.dataset.method;
                overlay.querySelectorAll('.pf-method').forEach(t => t.classList.remove('active'));
                overlay.querySelectorAll('.pf-section').forEach(s => s.classList.remove('active'));
                tab.classList.add('active');
                overlay.querySelector('#pf-sec-' + method).classList.add('active');
                me._activeMethod = method;
            });
        });

        // Card number formatting
        const cardNum = overlay.querySelector('#pf-card-num');
        if (cardNum) {
            cardNum.addEventListener('input', (e) => {
                let v = e.target.value.replace(/\D/g, '').substring(0, 16);
                e.target.value = v.replace(/(\d{4})/g, '$1 ').trim();
            });
        }
        const cardExp = overlay.querySelector('#pf-card-exp');
        if (cardExp) {
            cardExp.addEventListener('input', (e) => {
                let v = e.target.value.replace(/\D/g, '').substring(0, 4);
                if (v.length >= 2) v = v.substring(0, 2) + ' / ' + v.substring(2);
                e.target.value = v;
            });
        }

        // Pay button
        overlay.querySelector('#pf-pay-btn').addEventListener('click', () => me._submit());

        // Retry
        overlay.querySelector('#pf-retry-btn').addEventListener('click', () => {
            overlay.querySelector('#pf-result-fail').classList.remove('pf-show');
            overlay.querySelector('#pf-form-area').style.display = '';
            const btn = overlay.querySelector('#pf-pay-btn');
            btn.disabled = false;
            btn.innerHTML = 'Pay ' + formatINR(me._opts.amount || 0);
        });
    };

    PayFlow.prototype._submit = async function () {
        const overlay = this._overlay;
        const opts = this._opts;
        const btn = overlay.querySelector('#pf-pay-btn');

        btn.disabled = true;
        btn.innerHTML = '<span class="pf-spinner"></span>Processing…';

        const body = {
            order_ref: opts.order_ref,
            method: this._activeMethod,
            email: this._val('#pf-nb-email'),
            contact: this._val('#pf-nb-contact') || this._val('#pf-wallet-phone'),
            vpa: this._val('#pf-vpa'),
            card_number: this._val('#pf-card-num'),
            card_expiry: this._val('#pf-card-exp'),
            card_cvv: this._val('#pf-card-cvv'),
            card_name: this._val('#pf-card-name'),
        };

        try {
            const url = `${this._baseUrl}/pay/${opts.order_ref}`;
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await resp.json();

            overlay.querySelector('#pf-form-area').style.display = 'none';

            if (data.status === 'captured') {
                overlay.querySelector('#pf-ok-ref').textContent = data.payment_ref || '';
                overlay.querySelector('#pf-result-ok').classList.add('pf-show');
                if (typeof opts.handler === 'function') {
                    opts.handler({
                        payment_ref: data.payment_ref,
                        order_ref: opts.order_ref,
                        status: data.status,
                    });
                }
            } else {
                overlay.querySelector('#pf-result-fail').classList.add('pf-show');
                if (typeof opts.handler === 'function') {
                    opts.handler({ status: data.status || 'failed', order_ref: opts.order_ref });
                }
            }
        } catch (err) {
            overlay.querySelector('#pf-form-area').style.display = 'none';
            overlay.querySelector('#pf-result-fail').classList.add('pf-show');
        }
    };

    PayFlow.prototype._val = function (selector) {
        const el = this._overlay && this._overlay.querySelector(selector);
        return el ? el.value.trim() : '';
    };

    PayFlow.prototype.close = function () {
        if (!this._overlay) return;
        const overlay = this._overlay;
        overlay.classList.remove('pf-visible');
        setTimeout(() => {
            if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        }, 300);
        this._overlay = null;
        if (typeof this._opts.onDismiss === 'function') {
            this._opts.onDismiss();
        }
    };

    return PayFlow;
});
