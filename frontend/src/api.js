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
            localStorage.removeItem('token')
            window.location.href = '/'
        }
        return Promise.reject(err)
    }
)

export default api
