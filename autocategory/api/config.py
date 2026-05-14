from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM Configuration
    llama_base_url: str = "http://llama-server:8080"
    llama_model: str = "gemma4-e4b"  # model name dùng trong API call
    protonx_api_key: str = ""

    # Vector DB
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "categories"

    # Database
    database_url: str = "postgresql://autocategory:change_me@localhost:5432/autocategory"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # JWT Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 30
    
    # Rate Limiting
    default_rate_limit_per_minute: int = 60
    default_rate_limit_per_day: int = 1000
    
    # CORS
    cors_origins: str = "*"

    # Files
    categories_json_path: str = "/app/data/categories.json"
    log_level: str = "INFO"
    log_file: str = "/app/logs/autocategory.log"
    
    # Feature flags
    enable_image_generation: bool = True
    enable_training: bool = True
    
    # Data retention
    data_retention_days: int = 90

    # Category Attributes
    category_attributes_json_path: str = "/app/data/category_attributes.json"

    # Omni Sync
    omni_base_url: str = ""  # e.g. https://your-api.example.com
    omni_sync_mode: str = "manual"  # "manual" or "auto"
    omni_sync_interval_hours: int = 24


settings = Settings()
