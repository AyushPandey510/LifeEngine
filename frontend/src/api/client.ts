import axios from 'axios'
import { useAuthStore } from '../store/auth.store'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState()
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// Handle 401 errors and try to refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const { refreshToken, logout } = useAuthStore.getState()
      
      if (refreshToken) {
        try {
          const response = await axios.post('/api/v1/auth/refresh', {}, {
            headers: { Authorization: `Bearer ${refreshToken}` }
          })
          const { access_token, refresh_token } = response.data
          const { user, setAuth } = useAuthStore.getState()
          if (user) {
            setAuth(user, access_token, refresh_token)
          }
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch {
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