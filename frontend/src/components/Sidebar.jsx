import React from 'react'
import { useAuth } from '../context/AuthContext'
import { Zap, LayoutDashboard, BarChart3, ShieldAlert, LogOut } from 'lucide-react'
import toast from 'react-hot-toast'

const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} />, alwaysShow: true },
    { id: 'admin-stats', label: 'System Stats', icon: <BarChart3 size={20} />, alwaysShow: true },
    { id: 'admin-flagged', label: 'Flagged TXNs', icon: <ShieldAlert size={20} />, alwaysShow: true },
]

export default function Sidebar({ activeTab, setActiveTab }) {
    const { user, logout } = useAuth()

    const handleLogout = () => {
        logout()
        toast.success('Logged out')
    }

    return (
        <aside className="sidebar glass">
            <div className="sidebar-logo">
                <Zap size={26} className="logo-icon" />
                <span>PayFlow</span>
            </div>

            <nav className="sidebar-nav">
                {navItems.map(item => (
                    <button
                        key={item.id}
                        className={`nav-btn ${activeTab === item.id ? 'active' : ''}`}
                        onClick={() => setActiveTab(item.id)}
                    >
                        {item.icon}
                        <span>{item.label}</span>
                        {activeTab === item.id && <div className="nav-indicator" />}
                    </button>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="user-card glass">
                    <div className="user-avatar">
                        {user?.email?.[0]?.toUpperCase() || 'U'}
                    </div>
                    <div className="user-info">
                        <p className="user-email">{user?.email?.split('@')[0]}</p>
                        <p className="user-sub">{user?.email}</p>
                    </div>
                </div>
                <button className="logout-btn" onClick={handleLogout}>
                    <LogOut size={18} /> Logout
                </button>
            </div>
        </aside>
    )
}
