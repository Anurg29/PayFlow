import React, { useState, useEffect, useCallback } from 'react'
import api from './api'
import toast from 'react-hot-toast'
import { QrCode, CreditCard, Building2, TrendingUp, CheckCircle2, XCircle, RefreshCw, AlertTriangle, Clock } from 'lucide-react'

const FMT = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

const METHOD_ICONS = {
    upi: <QrCode size={20} />,
    card: <CreditCard size={20} />,
    netbanking: <Building2 size={20} />,
}

function StatusBadge({ status }) {
    const map = {
        success: { color: 'badge-success', icon: <CheckCircle2 size={12} /> },
        failed: { color: 'badge-danger', icon: <XCircle size={12} /> },
        refunded: { color: 'badge-gray', icon: <RefreshCw size={12} /> },
        processing: { color: 'badge-warning', icon: <Clock size={12} /> },
        pending: { color: 'badge-warning', icon: <Clock size={12} /> },
    }
    const { color, icon } = map[status] || map.pending
    return <span className={`badge ${color}`}>{icon} {status}</span>
}

function TxnCard({ txn, onRefund }) {
    const [refunding, setRefunding] = useState(false)

    const handleRefund = async () => {
        if (!window.confirm('Refund this transaction?')) return
        setRefunding(true)
        try {
            await onRefund(txn.id)
            toast.success('Refund processed!')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Refund failed')
        } finally { setRefunding(false) }
    }

    return (
        <div className={`txn-card glass ${txn.is_flagged ? 'flagged' : ''}`}>
            <div className="txn-icon">{METHOD_ICONS[txn.payment_method] || <CreditCard size={20} />}</div>
            <div className="txn-info">
                <div className="txn-key">{txn.idempotency_key}</div>
                <div className="txn-meta">
                    {new Date(txn.created_at).toLocaleString()} · {txn.payment_method.toUpperCase()}
                    {txn.is_flagged && <span className="flag-chip"><AlertTriangle size={11} /> Flagged</span>}
                </div>
                <StatusBadge status={txn.status} />
            </div>
            <div className="txn-right">
                <div className={`txn-amount ${txn.status === 'success' ? 'amount-success' : txn.status === 'failed' ? 'amount-danger' : ''}`}>
                    {FMT.format(txn.amount)}
                </div>
                {txn.status === 'success' && (
                    <button className="refund-btn" onClick={handleRefund} disabled={refunding}>
                        {refunding ? <span className="spinner-sm" /> : <><RefreshCw size={13} /> Refund</>}
                    </button>
                )}
            </div>
        </div>
    )
}

export default function TransactionsTab() {
    const [txns, setTxns] = useState([])
    const [loading, setLoading] = useState(true)
    const [stats, setStats] = useState({ total: 0, volume: 0 })

    const fetchTxns = useCallback(async () => {
        setLoading(true)
        try {
            const res = await api.get('/transactions/')
            setTxns(res.data)
            const vol = res.data.filter(t => t.status === 'success').reduce((s, t) => s + t.amount, 0)
            setStats({ total: res.data.length, volume: vol })
        } catch (err) {
            toast.error('Failed to fetch transactions')
        } finally { setLoading(false) }
    }, [])

    const handleRefund = async (id) => {
        await api.post(`/transactions/${id}/refund`)
        fetchTxns()
    }

    useEffect(() => { fetchTxns() }, [fetchTxns])

    return (
        <div className="panel glass">
            <div className="panel-header">
                <div>
                    <h2 className="panel-title">My Transactions</h2>
                    <p className="panel-sub">{FMT.format(stats.volume)} processed · {stats.total} total</p>
                </div>
                <button className="icon-btn" onClick={fetchTxns} title="Refresh">
                    <RefreshCw size={18} className={loading ? 'spin' : ''} />
                </button>
            </div>

            <div className="txn-list">
                {loading ? (
                    Array.from({ length: 4 }).map((_, i) => <div key={i} className="txn-skeleton pulse" />)
                ) : txns.length === 0 ? (
                    <div className="empty-state">
                        <TrendingUp size={40} opacity={0.3} />
                        <p>No transactions yet. Send your first payment!</p>
                    </div>
                ) : (
                    txns.map(t => <TxnCard key={t.id} txn={t} onRefund={handleRefund} />)
                )}
            </div>
        </div>
    )
}
