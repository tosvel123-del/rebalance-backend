from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Stock Portfolio Rebalance Notifier"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    FERNET_KEY: str = "b3ZlcmZsb3ctc2VjcmV0LWtleS1tdXN0LWJlLTMyLWJ5dGVzPQ=="
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    POSTGRES_USER: str = "rebalance"
    POSTGRES_PASSWORD: str = "rebalance123"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "rebalance"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

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
