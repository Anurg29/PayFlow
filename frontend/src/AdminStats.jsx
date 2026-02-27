import React, { useEffect, useState } from 'react'
import api from './api'
import toast from 'react-hot-toast'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { TrendingUp, CheckCircle2, XCircle, ShieldAlert, RefreshCw, IndianRupee } from 'lucide-react'

const FMT = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

function StatCard({ icon, label, value, color }) {
    return (
        <div className={`stat-card glass stat-${color}`}>
            <div className="stat-icon">{icon}</div>
            <div>
                <p className="stat-label">{label}</p>
                <h3 className="stat-value">{value}</h3>
            </div>
        </div>
    )
}

export default function AdminStats() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)

    const fetchStats = async () => {
        setLoading(true)
        try {
            const res = await api.get('/admin/stats')
            setStats(res.data)
        } catch (err) {
            if (err.response?.status === 403)
                toast.error('Admin access required')
            else toast.error('Failed to load stats')
        } finally { setLoading(false) }
    }

    useEffect(() => { fetchStats() }, [])

    const chartData = stats ? [
        { name: 'Success', value: stats.success_count, fill: '#10b981' },
        { name: 'Failed', value: stats.failed_count, fill: '#ef4444' },
        { name: 'Flagged', value: stats.flagged_count, fill: '#f59e0b' },
    ] : []

    const successRate = stats && stats.total_transactions > 0
        ? ((stats.success_count / stats.total_transactions) * 100).toFixed(1)
        : 0

    return (
        <div className="admin-page">
            <div className="admin-header">
                <h2>System Statistics</h2>
                <button className="icon-btn" onClick={fetchStats}><RefreshCw size={18} className={loading ? 'spin' : ''} /></button>
            </div>

            {loading ? (
                <div className="loading-grid">
                    {Array.from({ length: 4 }).map((_, i) => <div key={i} className="stat-skeleton pulse" />)}
                </div>
            ) : stats ? (
                <>
                    <div className="stats-grid">
                        <StatCard icon={<IndianRupee size={24} />} label="Total Volume" value={FMT.format(stats.total_amount)} color="blue" />
                        <StatCard icon={<TrendingUp size={24} />} label="Total Transactions" value={stats.total_transactions} color="purple" />
                        <StatCard icon={<CheckCircle2 size={24} />} label="Success Rate" value={`${successRate}%`} color="green" />
                        <StatCard icon={<ShieldAlert size={24} />} label="Flagged" value={stats.flagged_count} color="yellow" />
                    </div>

                    {/* Chart */}
                    <div className="chart-panel glass">
                        <h3 className="chart-title">Transaction Breakdown</h3>
                        <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={chartData} barSize={48}>
                                <XAxis dataKey="name" stroke="#64748b" tick={{ fill: '#94a3b8' }} />
                                <YAxis stroke="#64748b" tick={{ fill: '#94a3b8' }} allowDecimals={false} />
                                <Tooltip
                                    contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 }}
                                    cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                                />
                                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                                    {chartData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </>
            ) : (
                <div className="empty-state">
                    <XCircle size={40} opacity={0.3} />
                    <p>Could not load stats. You may need admin access.</p>
                </div>
            )}
        </div>
    )
}
