"""
Life Engine AI - Main Application
FastAPI backend for the Future Self Simulation Platform
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import structlog

from app.core.config import settings
from app.api.v1 import auth, chat, decisions, documents, health, insights, profile, users

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("application_startup", environment=settings.ENVIRONMENT)
    app.state.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.close()
    logger.info("application_shutdown")


# Create FastAPI application
app = FastAPI(
    title="Life Engine AI API",
    description="Future Self Simulation Platform - AI-powered personal assistant",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_rate_limit(request: Request, call_next):
    """Apply basic security headers and Redis-backed API rate limiting."""
    if request.url.path.startswith("/api/v1") and "/health" not in request.url.path:
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        key = f"rate:{client_ip}:{request.url.path}"
        try:
            current = await request.app.state.redis.incr(key)
            if current == 1:
                await request.app.state.redis.expire(key, 60)
            if current > settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again in a minute."},
                )
        except Exception as e:
            logger.warning("rate_limit_unavailable", error=str(e))

    try:
        response = await call_next(request)
    except Exception as e:
        logger.error("unhandled_request_error", path=request.url.path, error=str(e))
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again."},
        )
        origin = request.headers.get("origin")
        if origin in settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(decisions.router, prefix="/api/v1/decisions", tags=["Decisions"])
app.include_router(insights.router, prefix="/api/v1/insights", tags=["Insights"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Life Engine AI API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT != "production" else None
    }
