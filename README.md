# Life Engine AI

A future self simulation platform where users chat with an AI that represents their future self, personalized based on their profile, goals, habits, and past conversations.

## 🌟 Features

- **Personalized AI Conversations** - Chat with an AI that knows your goals, habits, and personality
- **Memory System** - The AI remembers your past conversations using vector embeddings (FAISS)
- **Profile Management** - Set your goals, habits, personality traits, and consistency score
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
│  │   Auth API   │  │  Chat API   │  │   Health API    │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ AI Service   │  │Memory Service│  │  Celery Workers │   │
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
POSTGRES_PORT=5432
POSTGRES_USER=lifeengine
POSTGRES_PASSWORD=your-password
POSTGRES_DB=lifeengine

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Providers (at least one required)
OPENAI_API_KEY=your-openai-key  # Optional
GEMINI_API_KEY=your-gemini-key  # Optional

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Backend API | 8000 | http://localhost:8000 |
| PostgreSQL | 5433 | localhost:5433 |
| Redis | 6379 | localhost:6379 |
| pgAdmin | 5050 | http://localhost:5050 |

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Create new account
- `POST /api/v1/auth/login` - Login (returns JWT tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

### Chat
- `POST /api/v1/chat/message` - Send message to AI
- `GET /api/v1/chat/history/{session_id}` - Get conversation history

### Health
- `GET /api/v1/health` - Health check endpoint

## 🔐 Security Features

- JWT access tokens (15 min expiry)
- JWT refresh tokens (30 day expiry)
- OAuth2 password flow
- Password hashing (bcrypt)
- CORS protection
- Rate limiting (30 req/min)

## 🧪 Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Async ORM
- **PostgreSQL** - Primary database
- **Redis** - Cache & session storage
- **Celery** - Background task queue
- **FAISS** - Vector similarity search
- **OpenAI/Gemini** - AI language models

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **Axios** - HTTP client
- **React Router** - Navigation

## 📝 License

MIT License

## 👤 Author

Life Engine AI Team