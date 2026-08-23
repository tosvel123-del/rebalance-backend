from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Stock Portfolio Rebalance Notifier"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    FERNET_KEY: str = "b3ZlcmZsb3ctc2VjcmV0LWtleS1tdXN0LWJlLTMyLWJ5dGVzPQ=="
    JOB_TRIGGER_SECRET: str = ""
    ALLOW_DEMO_AUTH: bool = True
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    POSTGRES_USER: str = "rebalance"
    POSTGRES_PASSWORD: str = "rebalance123"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "rebalance"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    PRICE_CACHE_TTL_SECONDS: int = 300

    DATABASE_URL_ENV: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_ENV:
            url = self.DATABASE_URL_ENV
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        # 기본 SQLite 폴백 (Zero-Config 서버 구동용)
        return "sqlite+aiosqlite:///./rebalance.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()


def validate_production_settings() -> None:
    """Fail closed when a deploy accidentally uses development secrets."""
    if settings.ENVIRONMENT.lower() != "production":
        return

    insecure_values = {
        "super-secret-key-change-in-production",
        "b3ZlcmZsb3ctc2VjcmV0LWtleS1tdXN0LWJlLTMyLWJ5dGVzPQ==",
        "",
    }
    missing = [
        name
        for name, value in {
            "SECRET_KEY": settings.SECRET_KEY,
            "FERNET_KEY": settings.FERNET_KEY,
            "JOB_TRIGGER_SECRET": settings.JOB_TRIGGER_SECRET,
        }.items()
        if value in insecure_values
    ]
    if missing:
        raise RuntimeError(f"Production secrets must be configured: {', '.join(missing)}")
