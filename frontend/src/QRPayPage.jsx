import React, { useState, useEffect } from 'react'
import api from './api'
import toast from 'react-hot-toast'
import { QrCode, CreditCard, Building2, Send, IndianRupee, Store, Wallet } from 'lucide-react'

const METHODS = [
    { id: 'upi', label: 'UPI', icon: <QrCode size={22} /> },
    { id: 'card', label: 'Card', icon: <CreditCard size={22} /> },
    { id: 'netbanking', label: 'NetBanking', icon: <Building2 size={22} /> },
    { id: 'wallet', label: 'Wallet', icon: <Wallet size={22} /> },
]

const FMT = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

export default function QRPayPage({ token }) {
    const [merchant, setMerchant] = useState(null)
    const [loading, setLoading] = useState(true)
    const [amount, setAmount] = useState('')
    const [method, setMethod] = useState('upi')
    const [payLoading, setPayLoading] = useState(false)
    const [result, setResult] = useState(null)

    useEffect(() => {
        // Fetch merchant details from QR token
        const fetchMerchant = async () => {
            try {
                const res = await api.get(`/pay/qr/${token}/merchant`)
                setMerchant(res.data)
            } catch (err) {
                toast.error('Invalid or expired QR code')
            } finally {
                setLoading(false)
            }
        }
        fetchMerchant()
    }, [token])

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!amount || parseFloat(amount) <= 0) {
            toast.error('Enter a valid amount')
            return
        }
        setPayLoading(true)
        try {
            const res = await api.post(`/pay/qr/${token}`, {
                amount: Math.round(parseFloat(amount) * 100), // convert to paise
                method,
                vpa: method === 'upi' ? 'test@upi' : undefined,
                contact: '9999999999'
            })
            setResult(res.data)
            if (res.data.status === 'captured') {
                toast.success('Payment successful!')
            } else {
                toast.error('Payment failed')
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Payment error')
        } finally {
            setPayLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="splash">
                <div className="splash-spinner" />
            </div>
        )
    }

    if (!merchant) {
        return (
            <div className="splash">
                <h2>❌ Invalid QR Code</h2>
                <p>This QR code does not belong to any active merchant.</p>
            </div>
        )
    }

    if (result) {
        return (
            <div className="splash">
                <div className="panel glass" style={{ textAlign: 'center', padding: '40px' }}>
                    {result.status === 'captured' ? (
                        <>
                            <div style={{ fontSize: 60, marginBottom: 16 }}>✅</div>
                            <h2 style={{ marginBottom: 8, color: 'var(--success)' }}>Payment Successful!</h2>
                            <p style={{ color: 'var(--text-2)' }}>You paid {FMT.format(result.amount / 100)} to {merchant.business_name}</p>
                            <p style={{ marginTop: 16, fontSize: 13, color: 'var(--text-3)' }}>Ref: {result.payment_ref}</p>
                        </>
                    ) : (
                        <>
                            <div style={{ fontSize: 60, marginBottom: 16 }}>❌</div>
                            <h2 style={{ marginBottom: 8, color: 'var(--danger)' }}>Payment Failed</h2>
                            <p style={{ color: 'var(--text-2)' }}>Something went wrong. Please try again.</p>
                            <button className="btn-primary mt-auto" onClick={() => setResult(null)} style={{ marginTop: '20px' }}>
                                Try Again
                            </button>
                        </>
                    )}
                </div>
            </div>
        )
    }

    return (
        <div className="splash">
            <div className="panel glass max-w-md w-full" style={{ padding: '30px' }}>
                <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                    <Store size={40} style={{ color: 'var(--primary)', margin: '0 auto 10px' }} />
                    <h2 style={{ fontSize: '24px', fontWeight: 600 }}>{merchant.business_name}</h2>
                    <p style={{ color: 'var(--text-3)', fontSize: '14px' }}>Secure QR Payment</p>
                </div>

                <form onSubmit={handleSubmit} className="payment-form">
                    <div className="amount-field">
                        <div className="amount-prefix"><IndianRupee size={20} /></div>
                        <input
                            type="number"
                            className="amount-input"
                            placeholder="0.00"
                            min="1"
                            value={amount}
                            onChange={e => setAmount(e.target.value)}
                            required
                            autoFocus
                        />
                    </div>

                    <p className="field-label" style={{ marginTop: '20px' }}>Payment Method</p>
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

                    <button type="submit" className="btn-primary" style={{ marginTop: '30px' }} disabled={payLoading}>
                        {payLoading
                            ? <><span className="spinner" /> Processing...</>
                            : <><Send size={18} /> Pay {amount ? FMT.format(parseFloat(amount)) : ''}</>}
                    </button>
                </form>
            </div>
        </div>
    )
}
