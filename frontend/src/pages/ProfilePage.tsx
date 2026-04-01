import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useAuthStore } from '../store/auth.store'

interface Profile {
  display_name: string | null
  age: number | null
  goals: any[]
  habits: any[]
  consistency_score: number
  risk_tolerance: number
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const response = await api.get('/profile')
      setProfile(response.data)
    } catch (error) {
      // Profile might not exist yet
      setProfile(null)
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-text-secondary">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-surface border-b border-primary">
        <button
          onClick={() => navigate('/chat')}
          className="text-text-secondary hover:text-text-primary"
        >
          ← Back to Chat
        </button>
        <button
          onClick={handleLogout}
          className="text-text-secondary hover:text-accent"
        >
          Logout
        </button>
      </header>

      <div className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-bold text-text-primary mb-6">Your Profile</h1>

        <div className="space-y-6">
          {/* User Info */}
          <div className="bg-surface p-6 rounded-lg border border-primary">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Account</h2>
            <div className="space-y-2">
              <p className="text-text-secondary">
                <span className="text-text-primary">Email:</span> {user?.email}
              </p>
              <p className="text-text-secondary">
                <span className="text-text-primary">Plan:</span> {user?.plan || 'free'}
              </p>
            </div>
          </div>

          {/* Profile Stats */}
          {profile && (
            <div className="bg-surface p-6 rounded-lg border border-primary">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Your Stats</h2>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-background rounded">
                  <div className="text-3xl font-bold text-accent">{profile.consistency_score}</div>
                  <div className="text-sm text-text-secondary">Consistency Score</div>
                </div>
                <div className="text-center p-4 bg-background rounded">
                  <div className="text-3xl font-bold text-primary">{profile.risk_tolerance}</div>
                  <div className="text-sm text-text-secondary">Risk Tolerance</div>
                </div>
              </div>

              {profile.goals && profile.goals.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-text-primary font-medium mb-2">Goals</h3>
                  <ul className="space-y-2">
                    {profile.goals.map((goal: any, index: number) => (
                      <li key={index} className="text-text-secondary">
                        • {goal.description}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Message */}
          {!profile && (
            <div className="bg-surface p-6 rounded-lg border border-primary text-center">
              <p className="text-text-secondary">
                Complete your profile by chatting with your future self. 
                The more you talk, the better it gets to know you!
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}