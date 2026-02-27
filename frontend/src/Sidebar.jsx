import React from 'react'
import { useAuth } from './AuthContext'
import { Zap, LayoutDashboard, BarChart3, ShieldAlert, UserCircle, LogOut, QrCode } from 'lucide-react'
import toast from 'react-hot-toast'

const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} />, alwaysShow: true },
    { id: 'my-qr', label: 'My QR Code', icon: <QrCode size={20} />, roles: ['merchant', 'admin'] },
    { id: 'admin-stats', label: 'System Stats', icon: <BarChart3 size={20} />, roles: ['admin'] },
    { id: 'admin-flagged', label: 'Flagged TXNs', icon: <ShieldAlert size={20} />, roles: ['admin'] },
    { id: 'profile', label: 'Profile', icon: <UserCircle size={20} />, alwaysShow: true },
]

const ROLE_META = {
    admin: { label: 'Admin', color: '#ef4444' },
    merchant: { label: 'Merchant', color: '#f59e0b' },
    user: { label: 'User', color: '#10b981' },
}

export default function Sidebar({ activeTab, setActiveTab }) {
    const { user, logout } = useAuth()

    // Decode role from JWT
    let role = 'user'
    try {
        const token = localStorage.getItem('token')
        const payload = JSON.parse(atob(token.split('.')[1]))
        role = payload.role || 'user'
    } catch { /* ignore */ }

    const rm = ROLE_META[role] || ROLE_META.user
    const avatarLetter = user?.email?.[0]?.toUpperCase() || 'U'
    const username = user?.email?.split('@')[0] || 'User'

    const handleLogout = () => {
        logout()
        toast.success('Logged out successfully 👋')
    }

    return (
        <aside className="sidebar glass">
            {/* Logo */}
            <div className="sidebar-logo">
                <Zap size={26} className="logo-icon" />
                <span>PayFlow</span>
            </div>

            {/* Nav */}
            <nav className="sidebar-nav">
                {navItems.map(item => {
                    if (!item.alwaysShow && (!item.roles || !item.roles.includes(role))) return null;
                    return (
                        <button
                            key={item.id}
                            className={`nav-btn ${activeTab === item.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(item.id)}
                        >
                            {item.icon}
                            <span>{item.label}</span>
                            {activeTab === item.id && <div className="nav-indicator" />}
                        </button>
                    )
                })}
            </nav>

            {/* Footer — avatar + logout */}
            <div className="sidebar-footer">
                {/* Clickable user card → goes to profile */}
                <button
                    className={`user-card glass sidebar-profile-btn ${activeTab === 'profile' ? 'active' : ''}`}
                    onClick={() => setActiveTab('profile')}
                    title="View Profile"
                >
                    <div className="user-avatar">{avatarLetter}</div>
                    <div className="user-info">
                        <p className="user-email">{username}</p>
                        <p className="user-sub" style={{ color: rm.color }}>
                            {rm.label}
                        </p>
                    </div>
                    <UserCircle size={16} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
                </button>

                {/* Logout */}
                <button className="logout-btn" onClick={handleLogout}>
                    <LogOut size={16} /> Sign Out
                </button>
            </div>
        </aside>
    )
}
