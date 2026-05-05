"""
Application Configuration
Loads settings from environment variables using Pydantic
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


def _standardize_postgres_url(url: str) -> str:
    """Normalize provider URLs before applying a driver."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _postgres_url_with_driver(url: str, driver: str | None) -> str:
    url = _standardize_postgres_url(url)
    prefixes = (
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
        "postgresql://",
    )
    for prefix in prefixes:
        if url.startswith(prefix):
            base = "postgresql://"
            return base.replace("postgresql", f"postgresql+{driver}", 1) + url[len(prefix):] if driver else base + url[len(prefix):]
    return url


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Convert comma-separated ALLOWED_ORIGINS to list for CORS"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "lifeengine"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "lifeengine"
    DATABASE_URL_ENV: str = Field("", alias="DATABASE_URL")
    
    @property
    def DATABASE_URL(self) -> str:
        """Async database URL for SQLAlchemy."""
        if self.DATABASE_URL_ENV:
            return _postgres_url_with_driver(self.DATABASE_URL_ENV, "asyncpg")
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Sync database URL for Alembic."""
        if self.DATABASE_URL_ENV:
            return _postgres_url_with_driver(self.DATABASE_URL_ENV, None)
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    FAISS_DIR: str = "local_faiss_indexes"
    REDIS_URL_ENV: str = Field("", alias="REDIS_URL")
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL_ENV:
            return self.REDIS_URL_ENV
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # AI / LLM
    # AI / LLM (Groq)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_TIMEOUT_SECONDS: int = 60

    # Optional (for embeddings)
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
        
    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Create settings instance
settings = Settings()
