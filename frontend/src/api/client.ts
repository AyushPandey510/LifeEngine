import axios from 'axios'
import { useAuthStore } from '../store/auth.store'

// Base URL from env (best practice)
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})
// ✅ Add auth token to every request
api.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState()

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }

  return config
})

// ✅ Handle token refresh automatically
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const isRetryable = !status || (status >= 500 && status < 600)
    const isMultipart = originalRequest?.data instanceof FormData

    if (isRetryable && !isMultipart && (originalRequest._retries || 0) < 1) {
      originalRequest._retries = (originalRequest._retries || 0) + 1
      await new Promise((resolve) => setTimeout(resolve, 400))
      return api(originalRequest)
    }

    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const { refreshToken, logout, user, setAuth } = useAuthStore.getState()

      if (refreshToken) {
        try {
          const response = await axios.post(
            `${API_BASE}/api/v1/auth/refresh`,
            {},
            {
              headers: {
                Authorization: `Bearer ${refreshToken}`,
              },
            }
          )

          const { access_token, refresh_token } = response.data

          if (user) {
            setAuth(user, access_token, refresh_token)
          }

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`

          return api(originalRequest)
        } catch (err) {
          logout()
        }
      } else {
        logout()
      }
    }

    return Promise.reject(error)
  }
)

export default api
