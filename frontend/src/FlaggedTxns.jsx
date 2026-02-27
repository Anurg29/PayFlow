import React, { useEffect, useState } from 'react'
import api from './api'
import toast from 'react-hot-toast'
import { ShieldAlert, RefreshCw, AlertTriangle, QrCode, CreditCard, Building2, CheckCircle2 } from 'lucide-react'

const FMT = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })
const METHOD_ICONS = {
    upi: <QrCode size={18} />,
    card: <CreditCard size={18} />,
    netbanking: <Building2 size={18} />,
}

export default function FlaggedTxns() {
    const [txns, setTxns] = useState([])
    const [loading, setLoading] = useState(true)

    const fetchFlagged = async () => {
        setLoading(true)
        try {
            const res = await api.get('/admin/flagged')
            setTxns(res.data)
        } catch (err) {
            if (err.response?.status === 403) toast.error('Admin access required')
            else toast.error('Failed to load flagged transactions')
        } finally { setLoading(false) }
    }

    useEffect(() => { fetchFlagged() }, [])

    return (
        <div className="admin-page">
            <div className="admin-header">
                <div>
                    <h2>Flagged Transactions</h2>
                    <p className="admin-sub">Caught by anomaly detection rules</p>
                </div>
                <button className="icon-btn" onClick={fetchFlagged}>
                    <RefreshCw size={18} className={loading ? 'spin' : ''} />
                </button>
            </div>

            {/* Rules Reference */}
            <div className="rules-grid">
                {[
                    { rule: 'High Value', threshold: 'Amount > ₹50,000', color: 'rule-red' },
                    { rule: 'Duplicate', threshold: 'Same amount within 60s', color: 'rule-yellow' },
                    { rule: 'High Frequency', threshold: '>5 transactions in 60s', color: 'rule-orange' },
                ].map(r => (
                    <div key={r.rule} className={`rule-chip glass ${r.color}`}>
                        <AlertTriangle size={14} />
                        <div>
                            <p className="rule-name">{r.rule}</p>
                            <p className="rule-threshold">{r.threshold}</p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Flagged List */}
            <div className="panel glass">
                <div className="panel-header">
                    <h3><ShieldAlert size={18} /> {txns.length} Flagged</h3>
                </div>
                <div className="txn-list">
                    {loading ? (
                        Array.from({ length: 3 }).map((_, i) => <div key={i} className="txn-skeleton pulse" />)
                    ) : txns.length === 0 ? (
                        <div className="empty-state">
                            <CheckCircle2 size={40} opacity={0.3} className="text-green" />
                            <p>System clean — no flagged transactions!</p>
                        </div>
                    ) : (
                        txns.map(txn => (
                            <div key={txn.id} className="txn-card glass flagged">
                                <div className="txn-icon">{METHOD_ICONS[txn.payment_method] || <CreditCard size={20} />}</div>
                                <div className="txn-info">
                                    <div className="txn-key">{txn.idempotency_key}</div>
                                    <div className="txn-meta">
                                        {new Date(txn.created_at).toLocaleString()} · User #{txn.user_id}
                                    </div>
                                    <span className="badge badge-warning"><AlertTriangle size={12} /> {txn.status}</span>
                                </div>
                                <div className="txn-right">
                                    <div className="txn-amount amount-warning">{FMT.format(txn.amount)}</div>
                                    <div className="method-tag">{txn.payment_method.toUpperCase()}</div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}
