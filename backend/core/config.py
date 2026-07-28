# backend/core/config.py — Phase 6
import os
from dotenv import load_dotenv
load_dotenv()

MODEL_NAME             = os.getenv("MODEL_NAME", "llama3:latest")
OLLAMA_URL             = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
REQUEST_TIMEOUT        = int(os.getenv("REQUEST_TIMEOUT", "120"))
LLM_MAX_RETRIES        = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_RETRY_DELAY        = int(os.getenv("LLM_RETRY_DELAY", "2"))

# Groq cloud LLM (alternative to local Ollama)
USE_GROQ               = os.getenv("USE_GROQ", "false").lower() == "true"
GROQ_API_KEY           = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL             = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

POSTGRES_HOST          = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT          = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB            = os.getenv("POSTGRES_DB", "ai_digital_team")
POSTGRES_USER          = os.getenv("POSTGRES_USER", "ai_admin")
POSTGRES_PASSWORD      = os.getenv("POSTGRES_PASSWORD", "")
DATABASE_URL           = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

REDIS_URL              = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL      = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_URL      = os.getenv("CELERY_RESULT_URL", "redis://localhost:6379/1")

JWT_SECRET_KEY         = os.getenv("JWT_SECRET_KEY", "change-this")
JWT_ALGORITHM          = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES     = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
RATE_LIMIT_PER_MINUTE  = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

APP_ENV                = os.getenv("APP_ENV", "development")
APP_VERSION            = os.getenv("APP_VERSION", "6.0.0")

# SMTP Configuration
SMTP_HOST              = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT              = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER              = os.getenv("SMTP_USER", "")
SMTP_PASSWORD          = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL             = os.getenv("FROM_EMAIL", "noreply@via-platform.local")
MEMORY_INJECTION_COUNT = int(os.getenv("MEMORY_INJECTION_COUNT", "3"))
COMPLEX_TASK_THRESHOLD = int(os.getenv("COMPLEX_TASK_THRESHOLD", "80"))

VALID_DEPARTMENTS = {
    # Tech division
    "backend", "security", "devops", "ai_research", "architecture", "frontend",
    # Business division (Phase 3)
    "hr", "finance", "marketing",
    # Special
    "presentation",
}

