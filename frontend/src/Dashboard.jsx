import React, { useState } from 'react'
import { useAuth } from './AuthContext'
import Sidebar from './Sidebar'
import TransactionsTab from './TransactionsTab'
import PaymentForm from './PaymentForm'
import AdminStats from './AdminStats'
import FlaggedTxns from './FlaggedTxns'
import MerchantQR from './MerchantQR'
import Profile from './Profile'

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState('dashboard')
    const { user } = useAuth()

    const renderContent = () => {
        switch (activeTab) {
            case 'dashboard': return <DashboardHome />
            case 'my-qr': return <MerchantQR />
            case 'admin-stats': return <AdminStats />
            case 'admin-flagged': return <FlaggedTxns />
            case 'profile': return <Profile />
            default: return <DashboardHome />
        }
    }

    return (
        <div className="app-shell">
            <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
            <main className="main-content">
                <div className="content-area">
                    {renderContent()}
                </div>
            </main>
        </div>
    )
}

function DashboardHome() {
    return (
        <div className="dashboard-grid">
            <div className="dashboard-left">
                <PaymentForm />
            </div>
            <div className="dashboard-right">
                <TransactionsTab />
            </div>
        </div>
    )
}
