from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "ENGEZ API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OPENAI_API_KEY: str = ""
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET: str = "engez-receipts"
    R2_PUBLIC_URL: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = ""
    SEED_ADMIN_EMAIL: str = "admin@engez.app"
    SEED_ADMIN_PASSWORD: str = "changeme123"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
