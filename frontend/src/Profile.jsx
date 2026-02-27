import React, { useState } from 'react'
import { useAuth } from './AuthContext'
import api from './api'
import toast from 'react-hot-toast'
import {
    User, Mail, Shield, KeyRound, Eye, EyeOff,
    CheckCircle2, LogOut, Calendar, Fingerprint
} from 'lucide-react'

export default function Profile() {
    const { user, logout } = useAuth()

    // Derive info from JWT payload
    const token = localStorage.getItem('token')
    let role = 'user'
    let joinedAt = null
    let tokenExp = null
    try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        role = payload.role || 'user'
        tokenExp = new Date(payload.exp * 1000)
        joinedAt = payload.iat ? new Date(payload.iat * 1000) : null
    } catch { /* ignore */ }

    const username = user?.email?.split('@')[0] || 'User'
    const avatarLetter = user?.email?.[0]?.toUpperCase() || 'U'

    // Change password state
    const [pwForm, setPwForm] = useState({ current: '', newPw: '', confirm: '' })
    const [showPw, setShowPw] = useState({ current: false, newPw: false, confirm: false })
    const [pwLoading, setPwLoading] = useState(false)

    const handleChangePassword = async (e) => {
        e.preventDefault()
        if (pwForm.newPw !== pwForm.confirm) {
            toast.error('New passwords do not match')
            return
        }
        if (pwForm.newPw.length < 6) {
            toast.error('Password must be at least 6 characters')
            return
        }
        setPwLoading(true)
        try {
            await api.post('/auth/change-password', {
                current_password: pwForm.current,
                new_password: pwForm.newPw,
            })
            toast.success('Password updated successfully!')
            setPwForm({ current: '', newPw: '', confirm: '' })
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to update password')
        } finally {
            setPwLoading(false)
        }
    }

    const handleLogout = () => {
        logout()
        toast.success('Logged out successfully')
    }

    const roleMeta = {
        admin: { label: 'Administrator', color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
        merchant: { label: 'Merchant', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
        user: { label: 'Standard User', color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
    }
    const rm = roleMeta[role] || roleMeta.user

    return (
        <div className="profile-page">

            {/* ── Hero Card ── */}
            <div className="profile-hero glass">
                <div className="profile-avatar-lg">
                    {avatarLetter}
                </div>
                <div className="profile-hero-info">
                    <h1 className="profile-name">{username}</h1>
                    <p className="profile-email-txt">{user?.email}</p>
                    <span className="profile-role-badge" style={{ color: rm.color, background: rm.bg }}>
                        <Shield size={12} />
                        {rm.label}
                    </span>
                </div>
                <button className="profile-logout-hero" onClick={handleLogout}>
                    <LogOut size={16} /> Sign Out
                </button>
            </div>

            <div className="profile-grid">

                {/* ── Account Details ── */}
                <div className="profile-card glass">
                    <div className="profile-card-header">
                        <User size={18} className="profile-card-icon" />
                        <h2>Account Details</h2>
                    </div>
                    <div className="profile-details-list">
                        <div className="profile-detail-row">
                            <span className="detail-label"><Mail size={14} /> Email</span>
                            <span className="detail-value">{user?.email}</span>
                        </div>
                        <div className="profile-detail-row">
                            <span className="detail-label"><Shield size={14} /> Role</span>
                            <span className="detail-value" style={{ color: rm.color }}>{rm.label}</span>
                        </div>
                        <div className="profile-detail-row">
                            <span className="detail-label"><Fingerprint size={14} /> Username</span>
                            <span className="detail-value">@{username}</span>
                        </div>
                        {tokenExp && (
                            <div className="profile-detail-row">
                                <span className="detail-label"><Calendar size={14} /> Session Expires</span>
                                <span className="detail-value">{tokenExp.toLocaleString()}</span>
                            </div>
                        )}
                    </div>
                    <div className="profile-session-badge">
                        <CheckCircle2 size={14} style={{ color: 'var(--success)' }} />
                        <span>Session active · Token valid until {tokenExp?.toLocaleTimeString()}</span>
                    </div>
                </div>

                {/* ── Change Password ── */}
                <div className="profile-card glass">
                    <div className="profile-card-header">
                        <KeyRound size={18} className="profile-card-icon" />
                        <h2>Change Password</h2>
                    </div>
                    <form onSubmit={handleChangePassword} className="profile-pw-form">
                        {[
                            { key: 'current', label: 'Current Password', placeholder: '••••••••' },
                            { key: 'newPw', label: 'New Password', placeholder: 'Min. 6 characters' },
                            { key: 'confirm', label: 'Confirm New Password', placeholder: 'Must match new password' },
                        ].map(({ key, label, placeholder }) => (
                            <div className="field" key={key}>
                                <label>{label}</label>
                                <div className="pw-input-wrap">
                                    <input
                                        type={showPw[key] ? 'text' : 'password'}
                                        placeholder={placeholder}
                                        value={pwForm[key]}
                                        onChange={e => setPwForm({ ...pwForm, [key]: e.target.value })}
                                        required
                                    />
                                    <button
                                        type="button"
                                        className="pw-toggle"
                                        onClick={() => setShowPw({ ...showPw, [key]: !showPw[key] })}
                                    >
                                        {showPw[key] ? <EyeOff size={16} /> : <Eye size={16} />}
                                    </button>
                                </div>
                            </div>
                        ))}
                        <button type="submit" className="btn-primary" disabled={pwLoading}>
                            {pwLoading
                                ? <><span className="spinner" /> Updating...</>
                                : <><KeyRound size={16} /> Update Password</>
                            }
                        </button>
                    </form>
                </div>

            </div>

            {/* ── Danger Zone ── */}
            <div className="profile-danger-zone glass">
                <div className="profile-card-header">
                    <LogOut size={18} style={{ color: 'var(--danger)' }} />
                    <h2 style={{ color: 'var(--danger)' }}>Sign Out</h2>
                </div>
                <p className="danger-desc">
                    This will end your current session and remove your token from this device.
                </p>
                <button className="logout-btn danger-logout" onClick={handleLogout}>
                    <LogOut size={16} /> Sign Out of PayFlow
                </button>
            </div>
        </div>
    )
}
