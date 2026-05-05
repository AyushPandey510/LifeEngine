# Life Engine AI

A future self simulation platform where users chat with an AI that represents their future self, personalized based on their profile, goals, habits, and past conversations.

## 🌟 Features

- **Personalized AI Conversations** - Chat with an AI that knows your goals, habits, and personality
- **Memory System** - The AI remembers your past conversations using vector embeddings (FAISS)
- **Document Uploads** - Upload resumes, cover letters, certificates, and notes so the AI can learn career, education, skill, and certification context
- **Profile Management** - Set your goals, habits, personality traits, and consistency score
- **Decision Simulator** - Compare two options using profile signals and personalized narratives
- **Insights Dashboard** - View consistency, goal, habit, and activity signals
- **JWT Authentication** - Secure login/register with access and refresh tokens
- **Real-time Chat** - Instant AI responses with latency tracking
- **Background Tasks** - Celery workers for memory storage and scheduled tasks
- **PostgreSQL Database** - User data, conversations, and profiles stored reliably
- **Redis Caching** - Session context and profile caching for performance

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vite + React + TypeScript)   │
│                    http://localhost:5173                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ Proxy /api → localhost:8000
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI + Python)              │
│                    http://localhost:8000                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Auth API   │  │  Chat API    │  │ Document API     │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ AI Service   │  │Memory Service│  │ Parser Service   │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└────────┬────────────┬──────────────┬─────────────────────────┘
         │            │              │
         ▼            ▼              ▼
    ┌─────────┐  ┌─────────┐  ┌─────────────┐
    │PostgreSQL│  │  Redis  │  │   Celery   │
    │ :5433   │  │ :6379   │  │  (Workers) │
    └─────────┘  └─────────┘  └─────────────┘
```

## 📁 Project Structure

```
Life_Engine/
├── docker-compose.yml          # Docker services configuration
├── README.md                   # This file
│
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py        # Login, register, token refresh
│   │   │   ├── chat.py        # Chat message endpoint
│   │   │   ├── decisions.py   # Decision simulator
│   │   │   ├── documents.py   # Resume, cover letter, certificate upload
│   │   │   ├── insights.py    # Insights dashboard
│   │   │   ├── profile.py     # Profile management
│   │   │   ├── users.py       # Data export and deletion
│   │   │   └── health.py      # Health check endpoint
│   │   ├── core/
│   │   │   ├── config.py      # Settings & configuration
│   │   │   └── security.py    # JWT & password utilities
│   │   ├── db/
│   │   │   ├── redis.py       # Redis client
│   │   │   └── session.py    # PostgreSQL async session
│   │   ├── models/
│   │   │   ├── db.py          # SQLAlchemy models (User, Profile, etc.)
│   │   │   └── schemas.py     # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ai_service.py  # AI/LLM integration (OpenAI, Gemini)
│   │   │   ├── document_service.py # Document parsing and signal extraction
│   │   │   └── memory_service.py  # FAISS vector store for memories
│   │   └── workers/
│   │       ├── celery_app.py  # Celery configuration
│   │       └── tasks.py       # Background tasks
│   ├── alembic/               # Database migrations
│   ├── faiss_indexes/         # Vector embeddings storage
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile
│   └── .env.example           # Environment variables template
│
└── frontend/                  # React + TypeScript frontend
    ├── src/
    │   ├── api/
    │   │   └── client.ts      # Axios API client with interceptors
    │   ├── pages/
    │   │   ├── ChatPage.tsx   # Main chat interface
    │   │   ├── LoginPage.tsx  # Login form
    │   │   ├── RegisterPage.tsx  # Registration form
    │   │   └── ProfilePage.tsx   # User profile management
    │   ├── store/
    │   │   └── auth.store.ts  # Zustand auth state management
    │   ├── App.tsx            # Main app component
    │   └── main.tsx           # Entry point
    ├── package.json
    ├── vite.config.ts         # Vite + proxy configuration
    ├── tailwind.config.js     # Tailwind CSS config
    └── tsconfig.json          # TypeScript config
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for local backend development)

### Option 1: Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Local Development

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## ☁️ Deployment

### Backend on Render

This repo includes `render.yaml` for a Render Blueprint. It creates:

- `life-engine-api` as a Docker web service from `backend/Dockerfile`
- `life-engine-db` as Render Postgres
- `life-engine-redis` as Render Key Value

Deploy steps:

1. Push the repo to GitHub/GitLab.
2. In Render, choose **New > Blueprint** and select this repo.
3. When Render prompts for `sync: false` values, set:
   - `ALLOWED_ORIGINS` to your Vercel URL, for example `https://your-app.vercel.app`
   - `GROQ_API_KEY`
   - `OPENAI_API_KEY` if you want production embeddings
4. Render runs `alembic upgrade head` before starting the API.

The backend listens on Render's `PORT` automatically and exposes health checks at `/api/v1/health`.

### Frontend on Vercel

Deploy the `frontend` directory as the Vercel project root.

Recommended Vercel settings:

- Framework Preset: `Vite`
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_URL=https://life-engine-api.onrender.com`

After Vercel gives you the final frontend URL, add that URL to Render's `ALLOWED_ORIGINS`.

## 🔧 Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
# App
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=lifeengine
POSTGRES_PASSWORD=your-password
POSTGRES_DB=lifeengine

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Groq
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TIMEOUT_SECONDS=60

# Embeddings for RAG
OPENAI_API_KEY=your-openai-key  # Optional for local development, recommended for production
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Local parsed-memory storage
FAISS_DIR=local_faiss_indexes

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### Using Groq

Set `GROQ_API_KEY` in `backend/.env`. The backend sends chat requests to Groq's OpenAI-compatible chat completions endpoint and streams responses internally where supported.

### Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Backend API | 8000 | http://localhost:8000 |
| PostgreSQL | 5433 | localhost:5433 |
| Redis | 6379 | localhost:6379 |
| pgAdmin | 5050 | http://localhost:5050 |

## 📄 Document Uploads

Life Engine AI can parse user documents and turn them into personalization signals. This helps the Future Self understand a user's career background, education, projects, certifications, skills, links, and recurring keywords.

Supported document categories:

- `resume`
- `cover_letter`
- `certificate`
- `other`

Supported file types:

- `.txt`
- `.md`
- `.json`
- `.docx`
- `.pdf` when `pypdf` is installed

The backend stores parsed text and extracted signals, not the raw uploaded file. Those signals are merged into `profile.personality.document_profile` and a summary is indexed into FAISS memory.

After pulling this feature, run:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

Upload from the UI:

1. Open `http://localhost:5173`
2. Use the paperclip button in the chat prompt box, or go to Profile
3. Select document type and upload a file

Upload with curl:

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=resume" \
  -F "file=@/path/to/resume.docx"
```

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Create new account
- `POST /api/v1/auth/login` - Login (returns JWT tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

### Chat
- `POST /api/v1/chat/message` - Send message to AI
- `GET /api/v1/chat/conversations` - List chat projects
- `POST /api/v1/chat/conversations` - Create a chat project
- `GET /api/v1/chat/history/{conversation_id}` - Get conversation history

### Profile, Decisions, Insights
- `GET /api/v1/profile` - Get profile used for personalization
- `PUT /api/v1/profile` - Update goals, habits, and personalization scores
- `POST /api/v1/decisions/simulate` - Simulate two options with scores and narratives
- `GET /api/v1/insights` - Get consistency, goal, habit, and activity insights

### Documents
- `POST /api/v1/documents` - Upload and parse a document for personalization
- `GET /api/v1/documents` - List parsed documents and extracted signals

### Privacy
- `GET /api/v1/users/me/data-export` - Export personal data, including document metadata/signals, as JSON
- `DELETE /api/v1/users/me` - Request account deletion

### Health
- `GET /api/v1/health` - Health check endpoint
- `GET /api/v1/health/ready` - Database and Redis readiness check
- `GET /api/v1/health/groq` - Groq connection and model readiness check

## 🔐 Security Features

- JWT access tokens (15 min expiry)
- JWT refresh tokens (30 day expiry)
- OAuth2 password flow
- Password hashing (bcrypt)
- CORS protection
- Redis-backed rate limiting (30 req/min by default)
- Security headers for content sniffing, clickjacking, referrer policy, and HSTS in production

## 🧪 Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Async ORM
- **PostgreSQL** - Primary database
- **Redis** - Cache & session storage
- **Celery** - Background task queue
- **FAISS** - Vector similarity search
- **Groq** - Primary AI language model
- **OpenAI embeddings** - Optional production embedding provider for RAG
- **pypdf** - PDF text extraction for document uploads

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **Axios** - HTTP client
- **React Router** - Navigation

## ✅ Verification

Run focused backend tests:

```bash
cd backend
./venv/bin/pytest tests/test_document_service.py tests/test_personalization_core.py
```

Run frontend build:

```bash
cd frontend
npm run build
```

## 📝 License

MIT License

## 👤 Author

Life Engine AI Team
