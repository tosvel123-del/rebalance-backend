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

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
