from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BeMyCa"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # DB
    DATABASE_URL: str = "postgresql://bemyca:bemyca_dev@localhost:5432/bemyca"
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # Anthropic
    ANTHROPIC_API_KEY: str = "mock"

    # AWS
    AWS_ACCESS_KEY_ID: str = "mock"
    AWS_SECRET_ACCESS_KEY: str = "mock"
    AWS_REGION: str = "ap-south-1"
    AWS_TEXTRACT_BUCKET: str = "bemyca-documents-dev"

    # GSP
    GSP_BASE_URL: str = "https://api.masters-india.com"
    GSP_USERNAME: str = "mock"
    GSP_PASSWORD: str = "mock"
    GSP_CLIENT_ID: str = "mock"
    GSP_CLIENT_SECRET: str = "mock"

    # WhatsApp
    WHATSAPP_TOKEN: str = "mock"
    WHATSAPP_PHONE_NUMBER_ID: str = "mock"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "bemyca-whatsapp-verify"

    # Razorpay
    RAZORPAY_KEY_ID: str = "mock"
    RAZORPAY_KEY_SECRET: str = "mock"

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
