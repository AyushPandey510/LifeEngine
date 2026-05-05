"""
Health Check Endpoints
Provides health status for monitoring and load balancers
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import structlog

from app.db.session import get_db
from app.db.redis import get_redis
from app.services.ai_service import check_groq_status

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check - returns OK if service is running"""
    return {
        "status": "healthy",
        "service": "lifeengine-api",
        "version": "1.0.0"
    }


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Readiness check - returns OK if service can handle requests
    Checks database and Redis connectivity
    """
    try:
        # Check database
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        db_status = "disconnected"
    
    try:
        # Check Redis
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        redis_status = "disconnected"
    
    is_ready = db_status == "connected" and redis_status == "connected"
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "database": db_status,
        "redis": redis_status
    }


@router.get("/ping")
async def ping():
    """Simple ping endpoint for load balancer probes"""
    return {"ping": "pong"}


@router.get("/health/groq")
async def groq_health_check():
    """GROQ connectivity and model readiness check."""
    return await check_groq_status()
