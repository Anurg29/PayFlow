import React, { useState } from 'react'
import { useAuth } from './AuthContext'
import toast from 'react-hot-toast'
import { LogIn, UserPlus, Zap, Shield, TrendingUp, Lock } from 'lucide-react'

export default function AuthPage() {
    const [tab, setTab] = useState('login')
    const [loading, setLoading] = useState(false)
    const { login, register } = useAuth()

    // Login state
    const [loginData, setLoginData] = useState({ email: '', password: '' })
    // Register state
    const [regData, setRegData] = useState({ name: '', email: '', password: '', role: 'user' })

    const handleLogin = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            await login(loginData.email, loginData.password)
            toast.success('Welcome back! 🎉')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Login failed')
        } finally { setLoading(false) }
    }

    const handleRegister = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            await register(regData.name, regData.email, regData.password, regData.role)
            toast.success('Account created! Welcome to PayFlow 🎉')
            // No setTab('login') needed — AuthContext sets user → App.jsx routes to Dashboard
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Registration failed')
        } finally { setLoading(false) }
    }

    return (
        <div className="auth-root">
            {/* Background Orbs */}
            <div className="orb orb-1" />
            <div className="orb orb-2" />
            <div className="orb orb-3" />

            <div className="auth-wrapper">
                {/* Left Panel - Branding */}
                <div className="auth-brand">
                    <div className="brand-logo">
                        <Zap size={36} />
                        <span>PayFlow</span>
                    </div>
                    <h1 className="brand-headline">
                        Next-Gen Payment<br />Infrastructure
                    </h1>
                    <p className="brand-sub">
                        Real-time transactions with enterprise-grade security, anomaly detection, and JWT authentication.
                    </p>
                    <div className="brand-features">
                        {[
                            { icon: <Shield size={18} />, text: 'JWT Role-Based Auth' },
                            { icon: <TrendingUp size={18} />, text: 'Real-Time Transaction State Machine' },
                            { icon: <Lock size={18} />, text: 'Anomaly Detection & Fraud Flagging' },
                        ].map((f, i) => (
                            <div key={i} className="feature-pill">
                                {f.icon} <span>{f.text}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Right Panel - Auth Form */}
                <div className="auth-card glass">
                    <div className="auth-tabs">
                        <button className={`auth-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => setTab('login')}>
                            <LogIn size={16} /> Sign In
                        </button>
                        <button className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => setTab('register')}>
                            <UserPlus size={16} /> Register
                        </button>
                    </div>

                    {tab === 'login' ? (
                        <form onSubmit={handleLogin} className="auth-form">
                            <h2>Welcome back</h2>
                            <p className="form-sub">Sign in to your PayFlow account</p>

                            <div className="field">
                                <label>Email</label>
                                <input type="email" placeholder="you@example.com" required
                                    value={loginData.email}
                                    onChange={e => setLoginData({ ...loginData, email: e.target.value })} />
                            </div>
                            <div className="field">
                                <label>Password</label>
                                <input type="password" placeholder="••••••••" required
                                    value={loginData.password}
                                    onChange={e => setLoginData({ ...loginData, password: e.target.value })} />
                            </div>
                            <button type="submit" className="btn-primary" disabled={loading}>
                                {loading ? <span className="spinner" /> : <><LogIn size={18} /> Sign In</>}
                            </button>
                        </form>
                    ) : (
                        <form onSubmit={handleRegister} className="auth-form">
                            <h2>Create account</h2>
                            <p className="form-sub">Join PayFlow in seconds</p>

                            <div className="field">
                                <label>Full Name</label>
                                <input type="text" placeholder="Anurag Rokade" required
                                    value={regData.name}
                                    onChange={e => setRegData({ ...regData, name: e.target.value })} />
                            </div>
                            <div className="field">
                                <label>Email</label>
                                <input type="email" placeholder="you@example.com" required
                                    value={regData.email}
                                    onChange={e => setRegData({ ...regData, email: e.target.value })} />
                            </div>
                            <div className="field">
                                <label>Password</label>
                                <input type="password" placeholder="••••••••" required
                                    value={regData.password}
                                    onChange={e => setRegData({ ...regData, password: e.target.value })} />
                            </div>
                            <div className="field">
                                <label>Role</label>
                                <select value={regData.role} onChange={e => setRegData({ ...regData, role: e.target.value })}>
                                    <option value="user">Standard User</option>
                                    <option value="admin">Administrator</option>
                                    <option value="merchant">Merchant</option>
                                </select>
                            </div>
                            <button type="submit" className="btn-primary" disabled={loading}>
                                {loading ? <span className="spinner" /> : <><UserPlus size={18} /> Create Account</>}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </div>
    )
}
