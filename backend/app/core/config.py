from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application configuration settings.
    
    This class uses pydantic-settings to automatically load environment variables
    from the .env file and perform type validation. It ensures that the application
    fails fast during startup if any critical environment variables are missing
    or invalid.
    """
    
    # Application basic settings
    PROJECT_NAME: str = "CrimeLens AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Database Settings
    DATABASE_URL: str = ""
    
    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Security/JWT Settings
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_VERIFICATION_METHOD: str = "secret"  # 'secret' (HS256) or 'jwks' (RS256)
    SUPABASE_JWKS_URL: Optional[str] = None
    AUTH_HEADER_PREFIX: str = "Bearer"

    @model_validator(mode="after")
    def compute_jwks_url(self) -> "Settings":
        if self.SUPABASE_URL and not self.SUPABASE_JWKS_URL:
            # Supabase ES256/RS256 signing keys (legacy /jwt/jwk is often empty)
            self.SUPABASE_JWKS_URL = (
                f"{self.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
            )
        return self

    # Pydantic v2 configuration style
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Storage Settings
    STORAGE_BUCKET_NAME: str = "evidence"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_MIME_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "application/pdf",
        "video/mp4"
    ]
    EVIDENCE_UPLOAD_PATH: str = "evidence"
    SIGNED_URL_EXPIRATION_SECONDS: int = 3600

    # AI / MLOps paths (relative to repository root when deployed with /app layout)
    AI_MODELS_DIR: str = "ai/models"
    AI_REGISTRY_DIR: str = "ai/registry"
    AI_REGISTRY_INDEX: str = "ai/registry/registry_index.json"
    AI_ACTIVE_VERSION_FILE: str = "ai/registry/active_version.json"
    AI_TRAINING_STATISTICS: str = "ai/models/training_statistics.json"
    LOG_DIR: str = "logs"

    # Enterprise Hardening (Phase 9)
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    RATE_LIMIT_ENABLED: bool = True
    BACKUP_DIR: str = "backups"

# Expose a reusable settings object to be used throughout the application
settings = Settings()

