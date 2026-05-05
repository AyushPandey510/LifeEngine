import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, Brain, FileText, LogOut, Paperclip, Plus, RefreshCw, Send, Settings, Sparkles, X } from 'lucide-react'
import api from '../api/client'
import { useAuthStore } from '../store/auth.store'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface DecisionResult {
  options: {
    option: string
    score: number
    reasoning: string
  }[]
  recommended: string
}

interface Insights {
  consistency_score: number
  consistency_trend: number[]
  top_goals: Array<{ description: string }>
  habit_streaks: Array<{ name: string; streak?: number }>
  weekly_insights: string[]
}

interface Conversation {
  id: string
  title: string
  message_count: number
}

const SELECTED_CONVERSATION_KEY = 'lifeengine:selectedConversationId'

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'chat' | 'decision' | 'insights'>('chat')
  const [decisionText, setDecisionText] = useState('')
  const [options, setOptions] = useState<string[]>(["", ""])
  const [decisionResult, setDecisionResult] = useState<DecisionResult | null>(null)
  const [insights, setInsights] = useState<Insights | null>(null)
  const [documentFile, setDocumentFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState<'resume' | 'cover_letter' | 'certificate' | 'other'>('resume')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(() => localStorage.getItem(SELECTED_CONVERSATION_KEY))
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { logout, user } = useAuthStore()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const accessToken = useAuthStore((state) => state.accessToken)

  useEffect(() => {
    if (!accessToken) return
    loadConversations()
  }, [accessToken])

  useEffect(() => {
    if (selectedConversationId) {
      localStorage.setItem(SELECTED_CONVERSATION_KEY, selectedConversationId)
      loadHistory(selectedConversationId)
    }
  }, [selectedConversationId])

  useEffect(() => {
    if (mode === 'insights') {
      setInsights(null)
      api.get('/insights')
        .then((response) => setInsights(response.data))
        .catch((err) => setError(extractErrorMessage(err)))
    }
  }, [mode])

  // Safely converts any FastAPI error shape to a readable string
  const extractErrorMessage = (error: any): string => {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d: any) => d.msg ?? JSON.stringify(d)).join('; ')
    }
    return 'I hit a temporary issue. Try again in a moment.'
  }

  const loadConversations = async () => {
    setLoadingHistory(true)
    setError('')
    try {
      const response = await api.get('/chat/conversations')
      const items = response.data as Conversation[]
      setConversations(items)
      const storedId = localStorage.getItem(SELECTED_CONVERSATION_KEY)
      const nextId = items.find((item) => item.id === storedId)?.id || items[0]?.id || null
      if (nextId) {
        if (nextId === selectedConversationId) {
          await loadHistory(nextId)
        } else {
          setSelectedConversationId(nextId)
        }
      } else {
        setMessages([])
        setLoadingHistory(false)
      }
    } catch (err: any) {
      setError(extractErrorMessage(err))
      setLoadingHistory(false)
    }
  }

  const loadHistory = async (conversationId: string) => {
    setLoadingHistory(true)
    setError('')
    try {
      const response = await api.get(`/chat/history/${conversationId}`)
      setMessages(response.data.map((item: any) => ({
        role: item.role,
        content: item.content
      })))
    } catch (err: any) {
      setError(extractErrorMessage(err))
    } finally {
      setLoadingHistory(false)
    }
  }

const createConversation = async () => {
  setSelectedConversationId(null)
  setMessages([])
}

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if ((!input.trim() && !documentFile) || loading) return

    const userMessage = input.trim()
    const fileToUpload = documentFile
    setInput('')
    setDocumentFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    if (fileToUpload) {
      setMessages((prev) => [...prev, { role: 'user', content: `Uploaded ${fileToUpload.name}` }])
    }
    if (userMessage) {
      setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    }
    setLoading(true)

    try {
      let conversationId = selectedConversationId
      if (!conversationId) {
        conversationId = null
      }
      let uploadSummary = ''
      if (fileToUpload) {
        const formData = new FormData()
        formData.append('document_type', documentType)
        formData.append('file', fileToUpload)
        const uploadResponse = await api.post('/documents', formData)
        uploadSummary = uploadResponse.data.summary || `${fileToUpload.name} was parsed and added to your context.`
        setMessages((prev) => [...prev, { role: 'assistant', content: uploadSummary }])
      }

      if (userMessage) {
        const response = await api.post('/chat/message', {
          message: uploadSummary ? `${userMessage}\n\nContext just uploaded: ${uploadSummary}` : userMessage,
          conversation_id: conversationId,
        })
        setMessages((prev) => [...prev, { role: 'assistant', content: response.data.message }])
        loadConversations()
      }
    } catch (error: any) {
      setMessages((prev) => [...prev, { role: 'assistant', content: extractErrorMessage(error) }])
    } finally {
      setLoading(false)
    }
  }

  const simulateDecision = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setDecisionResult(null)
    try {
      const response = await api.post('/decisions/simulate', {
        decision_text: decisionText,
        options: options.filter(o => o.trim() !== "")
      })
      setDecisionResult(response.data)
    } catch (error: any) {
      setError(extractErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-background text-text-primary">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-primary bg-surface px-4 py-3 sm:px-6">
        <div>
          <h1 className="text-xl font-bold">Life Engine AI</h1>
          <p className="text-sm text-text-secondary">{user?.display_name || 'Your Future Self'}</p>
        </div>
        <div className="flex items-center gap-2">
          <button title="Profile" onClick={() => navigate('/profile')} className="rounded border border-primary p-2 text-text-secondary hover:text-text-primary">
            <Settings size={18} />
          </button>
          <button title="Logout" onClick={handleLogout} className="rounded border border-primary p-2 text-text-secondary hover:text-accent">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-4 p-4 lg:grid-cols-[220px_1fr]">
        <nav className="flex gap-2 lg:flex-col">
          <button
            onClick={createConversation}
            className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded border border-primary bg-surface px-3 py-2 text-text-secondary hover:text-text-primary lg:justify-start"
          >
            <Plus size={18} />
            <span>New</span>
          </button>
          {[
            ['chat', Brain, 'Chat'],
            ['decision', Sparkles, 'Decision'],
            ['insights', BarChart3, 'Insights'],
          ].map(([key, Icon, label]) => (
            <button
              key={key as string}
              onClick={() => setMode(key as typeof mode)}
              className={`flex min-h-11 flex-1 items-center justify-center gap-2 rounded border px-3 py-2 lg:justify-start ${
                mode === key ? 'border-accent bg-accent text-white' : 'border-primary bg-surface text-text-secondary hover:text-text-primary'
              }`}
            >
              <Icon size={18} />
              <span>{label as string}</span>
            </button>
          ))}
          {conversations.length > 0 && (
            <div className="hidden border-t border-primary pt-3 lg:block">
              <div className="mb-2 flex items-center justify-between text-xs text-text-secondary">
                <span>Projects</span>
                <button title="Refresh projects" onClick={loadConversations} className="rounded p-1 hover:text-text-primary">
                  <RefreshCw size={14} />
                </button>
              </div>
              <div className="space-y-2">
                {conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    onClick={() => setSelectedConversationId(conversation.id)}
                    className={`w-full truncate rounded border px-3 py-2 text-left text-sm ${
                      selectedConversationId === conversation.id ? 'border-accent text-text-primary' : 'border-primary text-text-secondary hover:text-text-primary'
                    }`}
                    title={conversation.title}
                  >
                    {conversation.title}
                  </button>
                ))}
              </div>
            </div>
          )}
        </nav>

        {mode === 'chat' && (
          <section className="flex h-[calc(100vh-112px)] min-h-[560px] flex-col overflow-hidden rounded-lg border border-primary bg-surface">
            <div className="flex-1 space-y-4 overflow-y-auto p-4">
              {error && (
                <div className="rounded border border-red-400 bg-red-900/20 px-4 py-3 text-sm text-red-400">{error}</div>
              )}
              {loadingHistory && (
                <div className="inline-flex rounded-lg border border-primary bg-background px-4 py-3 text-text-secondary">
                  Loading history...
                </div>
              )}
              {!loadingHistory && messages.length === 0 && (
                <div className="mx-auto mt-16 max-w-xl text-center text-text-secondary">
                  <p className="text-lg text-text-primary">Start with what matters today.</p>
                  <p className="mt-2">Try: my goal is to deploy Life Engine this week, or ask a decision you are avoiding.</p>
                </div>
              )}

              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-2xl whitespace-pre-wrap rounded-lg px-4 py-3 ${msg.role === 'user' ? 'bg-primary' : 'border border-primary bg-background'}`}>
                    {msg.content}
                  </div>
                </div>
              ))}

              {loading && mode === 'chat' && (
                <div className="inline-flex rounded-lg border border-primary bg-background px-4 py-3 text-text-secondary">
                  Thinking...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="border-t border-primary p-3">
              {documentFile && (
                <div className="mb-2 flex flex-wrap items-center gap-2 rounded border border-primary bg-background px-3 py-2">
                  <FileText size={17} className="text-accent" />
                  <span className="max-w-[240px] truncate text-sm">{documentFile.name}</span>
                  <select
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value as typeof documentType)}
                    className="rounded border border-primary bg-surface px-2 py-1 text-sm outline-none focus:border-accent"
                  >
                    <option value="resume">Resume</option>
                    <option value="cover_letter">Cover letter</option>
                    <option value="certificate">Certificate</option>
                    <option value="other">Other</option>
                  </select>
                  <button
                    type="button"
                    title="Remove file"
                    onClick={() => {
                      setDocumentFile(null)
                      if (fileInputRef.current) {
                        fileInputRef.current.value = ''
                      }
                    }}
                    className="ml-auto rounded p-1 text-text-secondary hover:text-text-primary"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
              <div className="flex gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md,.json,.docx,.pdf,application/pdf"
                  onChange={(e) => setDocumentFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
                <button
                  type="button"
                  title="Attach document"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                  className="grid min-h-12 w-12 place-items-center rounded border border-primary bg-background text-text-secondary hover:text-text-primary disabled:opacity-50"
                >
                  <Paperclip size={18} />
                </button>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={documentFile ? 'Add an optional note about this document...' : 'Tell your future self what is happening...'}
                  className="min-h-12 flex-1 rounded border border-primary bg-background px-4 outline-none focus:border-accent"
                  disabled={loading}
                />
                <button title="Send" disabled={loading || (!input.trim() && !documentFile)} className="grid min-h-12 w-12 place-items-center rounded bg-accent text-white disabled:opacity-50">
                  <Send size={18} />
                </button>
              </div>
            </form>
          </section>
        )}

        {mode === 'decision' && (
          <section className="rounded-lg border border-primary bg-surface p-5">
            <h2 className="text-xl font-semibold">Decision Simulator</h2>
            <form onSubmit={simulateDecision} className="mt-5 grid gap-4">
              <textarea value={decisionText} onChange={(e) => setDecisionText(e.target.value)} required placeholder="What decision are you making?" className="min-h-24 rounded border border-primary bg-background p-3 outline-none focus:border-accent" />
              <div className="grid gap-4">
            {options.map((opt, index) => (
              <textarea
                key={index}
                value={opt}
                onChange={(e) => {
                  const newOptions = [...options]
                  newOptions[index] = e.target.value
                  setOptions(newOptions)
                }}
                placeholder={`Option ${index + 1}`}
                className="min-h-28 rounded border border-primary bg-background p-3 outline-none focus:border-accent"
              />
            ))}

            <button
              type="button"
              onClick={() => setOptions([...options, ""])}
              className="w-fit rounded border border-primary px-3 py-1 text-sm"
            >
              + Add Option
            </button>
            </div>
              <button disabled={loading} className="w-fit rounded bg-accent px-5 py-2 font-medium text-white disabled:opacity-60">
                {loading ? 'Simulating...' : 'Simulate'}
              </button>
            </form>

            {decisionResult && (
              <div className="mt-6 grid gap-4 md:grid-cols-2">
                {decisionResult.options.map((item) => (
                  <div key={item.option} className="rounded-lg border border-primary bg-background p-4">
                    <div className="text-sm text-text-secondary">{item.option}</div>
                    <div className="mt-2 text-3xl font-bold text-accent">{item.score}%</div>
                    <p className="mt-3 text-text-secondary">{item.reasoning}</p>
                  </div>
                ))}
                <div className="md:col-span-2 rounded-lg border border-accent bg-background p-4">
                  Recommended path: <span className="font-semibold text-accent">{decisionResult.recommended}</span>
                </div>
              </div>
            )}
          </section>
        )}

        {mode === 'insights' && (
          <section className="rounded-lg border border-primary bg-surface p-5">
            <h2 className="text-xl font-semibold">Insights</h2>
            {!insights ? (
              <p className="mt-5 text-text-secondary">Loading...</p>
            ) : (
              <div className="mt-5 grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border border-primary bg-background p-4">
                  <div className="text-sm text-text-secondary">Consistency</div>
                  <div className="mt-2 text-4xl font-bold text-accent">{insights.consistency_score}</div>
                </div>
                <div className="rounded-lg border border-primary bg-background p-4 md:col-span-2">
                  <div className="text-sm text-text-secondary">Weekly signal</div>
                  <div className="mt-3 flex items-end gap-2">
                    {insights.consistency_trend.map((value, index) => (
                      <div key={index} className="w-8 rounded-t bg-accent" style={{ height: `${Math.max(12, value)}px` }} />
                    ))}
                  </div>
                </div>
                <div className="rounded-lg border border-primary bg-background p-4 md:col-span-3">
                  <div className="text-sm text-text-secondary">What the system knows</div>
                  <ul className="mt-3 space-y-2">
                    {insights.weekly_insights.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </div>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}
