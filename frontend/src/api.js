import axios from 'axios'

// In production (Firebase Hosting), VITE_API_URL points to the Render backend.
// In development, it's empty so Vite's proxy handles the requests.
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/',
})

api.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

api.interceptors.response.use(
    res => res,
    err => {
        if (err.response?.status === 401) {
            const token = localStorage.getItem('token')
            // Only force-logout if there's no token or it's truly expired
            if (!token) {
                window.location.href = '/'
                return Promise.reject(err)
            }
            // Check if the token is actually expired
            try {
                const payload = JSON.parse(atob(token.split('.')[1]))
                const isExpired = payload.exp * 1000 < Date.now()
                if (isExpired) {
                    localStorage.removeItem('token')
                    window.location.href = '/'
                    return Promise.reject(err)
                }
            } catch {
                localStorage.removeItem('token')
                window.location.href = '/'
                return Promise.reject(err)
            }
            // Token exists and not expired — let component handle the error (show toast)
        }
        return Promise.reject(err)
    }
)

export default api
