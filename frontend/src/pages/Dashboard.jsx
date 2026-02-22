import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import Sidebar from '../components/Sidebar'
import TransactionsTab from '../components/TransactionsTab'
import PaymentForm from '../components/PaymentForm'
import AdminStats from '../components/AdminStats'
import FlaggedTxns from '../components/FlaggedTxns'

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState('dashboard')
    const { user } = useAuth()

    const renderContent = () => {
        switch (activeTab) {
            case 'dashboard':
                return <DashboardHome />
            case 'admin-stats':
                return <AdminStats />
            case 'admin-flagged':
                return <FlaggedTxns />
            default:
                return <DashboardHome />
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
