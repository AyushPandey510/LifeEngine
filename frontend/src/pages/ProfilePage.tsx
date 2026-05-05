import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Upload } from 'lucide-react'
import api from '../api/client'
import { useAuthStore } from '../store/auth.store'

interface Profile {
  display_name: string | null
  age: number | null
  goals: Array<{ title: string; category?: string; timeline?: string }>
  habits: Array<{ name: string; frequency?: string; streak?: number }>
  consistency_score: number
  risk_tolerance: number
}

interface UserDocument {
  id: string
  document_type: string
  filename: string
  extracted_signals: {
    skills?: string[]
    education?: string[]
    experience?: string[]
    certifications?: string[]
    document_keywords?: string[]
  }
  created_at: string
}

const emptyProfile: Profile = {
  display_name: '',
  age: null,
  goals: [],
  habits: [],
  consistency_score: 50,
  risk_tolerance: 50,
}

// ✅ FIX: Safely extract error message from any API error shape
const extractError = (error: any): string => {
  const detail = error?.response?.data?.detail
  if (!detail) return 'Something went wrong.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e: any) => {
        if (typeof e === 'string') return e
        if (e?.msg) return `${e.loc?.slice(-1)?.[0] ?? 'field'}: ${e.msg}`
        return JSON.stringify(e)
      })
      .join(', ')
  }
  return JSON.stringify(detail)
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(emptyProfile)
  const [goalText, setGoalText] = useState('')
  const [habitText, setHabitText] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [notice, setNotice] = useState('')
  const [noticeType, setNoticeType] = useState<'info' | 'error' | 'success'>('info')
  const [documents, setDocuments] = useState<UserDocument[]>([])
  const [documentType, setDocumentType] = useState('resume')
  const [documentFile, setDocumentFile] = useState<File | null>(null)
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  useEffect(() => {
    loadProfile()
  }, [])

  const showNotice = (msg: string, type: 'info' | 'error' | 'success' = 'info') => {
    setNotice(msg)
    setNoticeType(type)
  }

  const loadProfile = async () => {
    setNotice('')
    try {
      const [profileResult, documentsResult] = await Promise.allSettled([
        api.get('/profile'),
        api.get('/documents'),
      ])
      if (profileResult.status === 'fulfilled') {
        setProfile(profileResult.value.data)
      } else {
        showNotice('Could not load profile yet. You can retry from this page.', 'error')
      }
      if (documentsResult.status === 'fulfilled') {
        setDocuments(documentsResult.value.data)
      }
    } finally {
      setLoading(false)
    }
  }

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setNotice('')
    try {
      const goals = goalText.trim()
        ? [...(profile.goals || []), { title: goalText.trim(), category: 'personal', timeline: 'active' }]
        : profile.goals || []
      const habits = habitText.trim()
        ? [...(profile.habits || []), { name: habitText.trim(), frequency: 'daily', streak: 0 }]
        : profile.habits || []

      const payload = {
  display_name: profile.display_name || null,
  age: profile.age,
  consistency_score: profile.consistency_score,
  risk_tolerance: profile.risk_tolerance,

  // ✅ send objects, not strings
  goals: goals.map(g => ({
    title: g.title,
    category: g.category ?? 'personal',
    timeline: g.timeline ?? 'active',
  })),
  habits: habits.map(h => ({
    name: h.name,
    frequency: h.frequency ?? 'daily',
    streak: h.streak ?? 0,
  })),
}

const response = await api.put('/profile', payload)
      setProfile(response.data)
      setGoalText('')
      setHabitText('')
      showNotice('Profile saved. Your future-self prompt will use this immediately.', 'success')
    } catch (error: any) {
      showNotice(extractError(error), 'error')
    } finally {
      setSaving(false)
    }
  }

  const exportData = async () => {
    try {
      const response = await api.get('/users/me/data-export')
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'lifeengine-data-export.json'
      link.click()
      URL.revokeObjectURL(url)
    } catch (error: any) {
      showNotice(extractError(error), 'error')
    }
  }

  const uploadDocument = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!documentFile || uploading) return

    setUploading(true)
    setNotice('')
    try {
      const formData = new FormData()
      formData.append('document_type', documentType)
      formData.append('file', documentFile)

      const response = await api.post('/documents', formData)
      setDocuments((prev) => [response.data, ...prev])
      setDocumentFile(null)
      showNotice(response.data.summary || 'Document uploaded and added to your future-self context.', 'success')
    } catch (error: any) {
      showNotice(extractError(error), 'error')
    } finally {
      setUploading(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) {
    return <div className="min-h-screen grid place-items-center bg-background text-text-secondary">Loading...</div>
  }

  const noticeColors = {
    info: 'bg-background text-text-secondary',
    success: 'bg-background text-green-400',
    error: 'bg-background text-red-400',
  }

  return (
    <div className="min-h-screen bg-background text-text-primary">
      <header className="flex items-center justify-between px-6 py-4 bg-surface border-b border-primary">
        <button onClick={() => navigate('/chat')} className="text-text-secondary hover:text-text-primary">
          Back to Chat
        </button>
        <button onClick={handleLogout} className="text-text-secondary hover:text-accent">
          Logout
        </button>
      </header>

      <main className="max-w-3xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Your Profile</h1>
          <p className="text-text-secondary">{user?.email} · {user?.plan || 'free'} plan</p>
        </div>

        <form onSubmit={saveProfile} className="space-y-5 bg-surface border border-primary rounded-lg p-6">
          {notice && (
            <div className={`rounded px-4 py-3 text-sm ${noticeColors[noticeType]}`}>
              {notice}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm text-text-secondary">Display name</span>
              <input
                value={profile.display_name || ''}
                onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
                className="w-full rounded border border-primary bg-background px-3 py-2 outline-none focus:border-accent"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-text-secondary">Age</span>
              <input
                type="number"
                value={profile.age || ''}
                onChange={(e) => setProfile({ ...profile, age: e.target.value ? Number(e.target.value) : null })}
                className="w-full rounded border border-primary bg-background px-3 py-2 outline-none focus:border-accent"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm text-text-secondary">Consistency score</span>
              <input
                type="range"
                min="0"
                max="100"
                value={profile.consistency_score}
                onChange={(e) => setProfile({ ...profile, consistency_score: Number(e.target.value) })}
                className="w-full accent-[#E94560]"
              />
              <span className="text-sm">{profile.consistency_score}/100</span>
            </label>
            <label className="space-y-2">
              <span className="text-sm text-text-secondary">Risk tolerance</span>
              <input
                type="range"
                min="0"
                max="100"
                value={profile.risk_tolerance}
                onChange={(e) => setProfile({ ...profile, risk_tolerance: Number(e.target.value) })}
                className="w-full accent-[#E94560]"
              />
              <span className="text-sm">{profile.risk_tolerance}/100</span>
            </label>
          </div>

          <label className="space-y-2 block">
            <span className="text-sm text-text-secondary">Add goal</span>
            <input
              value={goalText}
              onChange={(e) => setGoalText(e.target.value)}
              placeholder="Example: build Life Engine MVP and deploy it"
              className="w-full rounded border border-primary bg-background px-3 py-2 outline-none focus:border-accent"
            />
          </label>

          {profile.goals.length > 0 && (
            <div className="space-y-1">
              <span className="text-sm text-text-secondary">Current goals</span>
              <ul className="space-y-1">
                {profile.goals.map((g, i) => (
                  <li key={i} className="flex items-center justify-between rounded border border-primary bg-background px-3 py-2 text-sm">
                    <span>{g.title}</span>
                    <button
                      type="button"
                      onClick={() => setProfile({ ...profile, goals: profile.goals.filter((_, idx) => idx !== i) })}
                      className="ml-3 text-text-secondary hover:text-red-400"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <label className="space-y-2 block">
            <span className="text-sm text-text-secondary">Add habit</span>
            <input
              value={habitText}
              onChange={(e) => setHabitText(e.target.value)}
              placeholder="Example: code for 90 focused minutes daily"
              className="w-full rounded border border-primary bg-background px-3 py-2 outline-none focus:border-accent"
            />
          </label>

          {profile.habits.length > 0 && (
            <div className="space-y-1">
              <span className="text-sm text-text-secondary">Current habits</span>
              <ul className="space-y-1">
                {profile.habits.map((h, i) => (
                  <li key={i} className="flex items-center justify-between rounded border border-primary bg-background px-3 py-2 text-sm">
                    <span>{h.name}</span>
                    <span className="ml-2 text-xs text-text-secondary">🔥 {h.streak ?? 0} day streak</span>
                    <button
                      type="button"
                      onClick={() => setProfile({ ...profile, habits: profile.habits.filter((_, idx) => idx !== i) })}
                      className="ml-3 text-text-secondary hover:text-red-400"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              disabled={saving}
              className="rounded bg-accent px-5 py-2 font-medium text-white disabled:opacity-60"
            >
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
            <button
              type="button"
              onClick={exportData}
              className="rounded border border-primary px-5 py-2 text-text-secondary hover:text-text-primary"
            >
              Export Data
            </button>
          </div>
        </form>

        <section className="mt-6 space-y-5 bg-surface border border-primary rounded-lg p-6">
          <div>
            <h2 className="text-xl font-semibold">Documents</h2>
            <p className="text-sm text-text-secondary">
              Upload resumes, cover letters, certificates, or notes to improve personalization.
            </p>
          </div>

          <form onSubmit={uploadDocument} className="grid gap-4 sm:grid-cols-[180px_1fr_auto]">
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="rounded border border-primary bg-background px-3 py-2 outline-none focus:border-accent"
            >
              <option value="resume">Resume</option>
              <option value="cover_letter">Cover letter</option>
              <option value="certificate">Certificate</option>
              <option value="other">Other</option>
            </select>

            <input
              type="file"
              accept=".txt,.md,.json,.docx,.pdf"
              onChange={(e) => setDocumentFile(e.target.files?.[0] || null)}
              className="rounded border border-primary bg-background px-3 py-2 text-sm text-text-secondary file:mr-3 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-text-primary"
            />

            <button
              disabled={uploading || !documentFile}
              className="inline-flex items-center justify-center gap-2 rounded bg-accent px-4 py-2 font-medium text-white disabled:opacity-60"
            >
              <Upload size={17} />
              {uploading ? 'Uploading' : 'Upload'}
            </button>
          </form>

          <div className="space-y-3">
            {documents.length === 0 ? (
              <p className="text-sm text-text-secondary">No documents uploaded yet.</p>
            ) : (
              documents.map((item) => (
                <div key={item.id} className="rounded border border-primary bg-background p-4">
                  <div className="flex items-start gap-3">
                    <FileText size={20} className="mt-1 text-accent" />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium">{item.filename}</div>
                      <div className="text-sm text-text-secondary">
                        {item.document_type.replace('_', ' ')}
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {[
                          ...(item.extracted_signals.skills || []),
                          ...(item.extracted_signals.document_keywords || []),
                        ]
                          .slice(0, 10)
                          .map((signal) => (
                            <span
                              key={signal}
                              className="rounded border border-primary px-2 py-1 text-xs text-text-secondary"
                            >
                              {signal}
                            </span>
                          ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  )
}