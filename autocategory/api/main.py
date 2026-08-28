import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from runtime_config import runtime_config
from routers import (
    admin, category, classify, auth, generate,
    admin_logs, admin_training, admin_config, admin_categories, admin_system, admin_llm
)
from database import engine, Base, SessionLocal, get_pool_status
from models import User, APIKey, RequestLog  # Import to register models
from middleware import RequestLoggingMiddleware, RateLimitMiddleware
import redis.asyncio as redis

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %z",
)
logger = logging.getLogger(__name__)


class _HealthAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HealthAccessFilter())
logging.getLogger("gunicorn.access").addFilter(_HealthAccessFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (production should use Alembic migrations)
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
    
    # Initialize Redis connection for rate limiting
    redis_client = None
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis successfully")
        app.state.redis_client = redis_client
    except Exception as e:
        if redis_client is not None:
            await redis_client.aclose()
        logger.warning(f"Redis connection failed, rate limiting will be disabled: {e}")
        app.state.redis_client = None
    
    # Load runtime config from DB (LLM provider, model, thinking, ...)
    db = None
    try:
        db = SessionLocal()
        runtime_config.load_from_db(db)
        logger.info("RuntimeConfig loaded: provider=%s", runtime_config.llm_provider)
    except Exception as e:
        logger.warning(f"RuntimeConfig load failed, using defaults: {e}")
    finally:
        if db is not None:
            db.close()

    # Restore persisted DeepSeek credentials/model after proxy restarts. This
    # network call intentionally happens after the startup DB session is closed.
    if runtime_config.llm_provider == "deepseek" and runtime_config.deepseek_api_key:
        try:
            proxy_url = settings.deepseek_proxy_url
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{proxy_url}/configure",
                    json={
                        "api_key": runtime_config.deepseek_api_key,
                        "model": runtime_config.deepseek_model,
                    },
                )
                response.raise_for_status()
            logger.info("DeepSeek proxy configuration restored from database")
        except Exception as e:
            logger.warning("Could not restore DeepSeek proxy configuration: %s", e)

    yield
    
    # Cleanup on shutdown
    from services.llm_service import close_llm_clients
    await close_llm_clients()
    if hasattr(app.state, "redis_client") and app.state.redis_client:
        await app.state.redis_client.aclose()


app = FastAPI(
    title="AutoCategory API",
    description="Tự động phân loại danh mục sản phẩm bằng LLM local với admin system",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware (must be first)
cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Request logging middleware (disabled - uncomment to re-enable DB request logging)
# app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(admin_logs.router, tags=["Admin - Logs"])
app.include_router(admin_training.router, tags=["Admin - Training Data"])
app.include_router(admin_config.router, tags=["Admin - Configuration"])
app.include_router(admin_categories.router, tags=["Admin - Categories"])
app.include_router(admin_system.router, tags=["Admin - System"])
app.include_router(admin_llm.router, tags=["Admin - LLM Provider"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(classify.router, prefix="/api", tags=["Classify"])
app.include_router(category.router, prefix="/api", tags=["Categories"])
app.include_router(generate.router, prefix="/api", tags=["Generate"])


@app.get("/api/health", tags=["Health"])
async def health():
    pool = get_pool_status()
    return {
        "status": "degraded" if pool["utilization"] >= 0.8 else "ok",
        "database_pool": pool,
        "llm_provider": runtime_config.llm_provider,
    }

