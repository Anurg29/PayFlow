import React, { useState } from 'react'
import api from './api'
import toast from 'react-hot-toast'
import { QrCode, CreditCard, Building2, Send, IndianRupee, AlertCircle } from 'lucide-react'

const METHODS = [
    { id: 'upi', label: 'UPI', icon: <QrCode size={22} /> },
    { id: 'card', label: 'Card', icon: <CreditCard size={22} /> },
    { id: 'netbanking', label: 'NetBanking', icon: <Building2 size={22} /> },
]

const FMT = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

export default function PaymentForm() {
    const [amount, setAmount] = useState('')
    const [method, setMethod] = useState('upi')
    const [loading, setLoading] = useState(false)
    const [lastTxn, setLastTxn] = useState(null)

    const PRESETS = [500, 1000, 5000, 25000, 75000]

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!amount || parseFloat(amount) <= 0) {
            toast.error('Enter a valid amount')
            return
        }
        setLoading(true)
        try {
            const key = `txn-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`
            const res = await api.post('/transactions/', {
                amount: parseFloat(amount),
                payment_method: method,
                idempotency_key: key,
            })
            setLastTxn(res.data)

            if (res.data.is_flagged) {
                toast(`⚠️ Payment flagged — anomaly detected!`, { icon: '🚨' })
            } else if (res.data.status === 'success') {
                toast.success(`${FMT.format(amount)} sent via ${method.toUpperCase()}!`)
            } else {
                toast.error(`Transaction ${res.data.status}`)
            }
            setAmount('')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Payment failed')
        } finally { setLoading(false) }
    }

    const isHighValue = parseFloat(amount) > 50000

    return (
        <div className="panel glass h-full flex-col">
            <div className="panel-header">
                <div>
                    <h2 className="panel-title">Send Payment</h2>
                    <p className="panel-sub">Powered by PayFlow engine</p>
                </div>
                <Send size={22} className="text-accent" />
            </div>

            <form onSubmit={handleSubmit} className="payment-form">
                {/* Amount Input */}
                <div className="amount-field">
                    <div className="amount-prefix"><IndianRupee size={20} /></div>
                    <input
                        type="number"
                        className={`amount-input ${isHighValue ? 'border-warning' : ''}`}
                        placeholder="0.00"
                        min="1"
                        value={amount}
                        onChange={e => setAmount(e.target.value)}
                        required
                    />
                </div>

                {isHighValue && (
                    <div className="warning-pill">
                        <AlertCircle size={14} /> Amount &gt; ₹50,000 will be flagged & reviewed
                    </div>
                )}

                {/* Preset Amounts */}
                <div className="presets">
                    {PRESETS.map(p => (
                        <button key={p} type="button" className={`preset-btn ${parseFloat(amount) === p ? 'active' : ''}`}
                            onClick={() => setAmount(String(p))}>
                            ₹{p >= 1000 ? `${p / 1000}k` : p}
                        </button>
                    ))}
                </div>

                {/* Payment Method */}
                <p className="field-label">Payment Method</p>
                <div className="method-grid">
                    {METHODS.map(m => (
                        <button key={m.id} type="button"
                            className={`method-card ${method === m.id ? 'active' : ''}`}
                            onClick={() => setMethod(m.id)}>
                            {m.icon}
                            <span>{m.label}</span>
                        </button>
                    ))}
                </div>

                <button type="submit" className="btn-primary mt-auto" disabled={loading}>
                    {loading
                        ? <><span className="spinner" /> Processing...</>
                        : <><Send size={18} /> Send {amount ? FMT.format(parseFloat(amount)) : 'Payment'}</>}
                </button>
            </form>

            {/* Last Transaction Result */}
            {lastTxn && (
                <div className={`last-txn-result ${lastTxn.status === 'success' ? 'result-success' : 'result-fail'}`}>
                    <p className="result-label">Last Transaction</p>
                    <p className="result-status">{lastTxn.status.toUpperCase()} {lastTxn.is_flagged ? '🚨' : '✅'}</p>
                    <p className="result-key">{lastTxn.idempotency_key}</p>
                </div>
            )}
        </div>
    )
}
