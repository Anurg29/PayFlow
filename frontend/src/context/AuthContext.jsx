import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const token = localStorage.getItem('token')
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]))
                if (payload.exp * 1000 > Date.now()) {
                    setUser({ email: payload.sub, token })
                } else {
                    localStorage.removeItem('token')
                }
            } catch { localStorage.removeItem('token') }
        }
        setLoading(false)
    }, [])

    const login = async (email, password) => {
        const res = await api.post('/auth/login-json', { email, password })
        localStorage.setItem('token', res.data.access_token)
        const payload = JSON.parse(atob(res.data.access_token.split('.')[1]))
        setUser({ email: payload.sub, token: res.data.access_token })
        return res.data
    }

    const register = async (name, email, password, role) => {
        // Step 1: Create the account
        await api.post('/auth/register', { name, email, password, role })
        // Step 2: Auto-login immediately after registration
        const loginRes = await api.post('/auth/login-json', { email, password })
        localStorage.setItem('token', loginRes.data.access_token)
        const payload = JSON.parse(atob(loginRes.data.access_token.split('.')[1]))
        setUser({ email: payload.sub, token: loginRes.data.access_token })
        return loginRes.data
    }

    const logout = () => {
        localStorage.removeItem('token')
        setUser(null)
    }

    return (
        <AuthContext.Provider value={{ user, login, register, logout, loading }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext)
