"""
Configuracion centralizada de la aplicacion.

Lee variables de entorno desde el archivo .env (ver .env) usando
pydantic-settings. Todo el resto del codigo importa `settings` desde aqui
en vez de leer os.environ directamente.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    SECRET_KEY: str = "universidad_secret_key_mb_system_2026"
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 dia

    DATABASE_URL: str = "sqlite:///./universidad.db"

    MAX_LOGIN_ATTEMPTS: int = 3
    LOCKOUT_MINUTES: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalizar_database_url(cls, v: str) -> str:
        if not v:
            return "sqlite:///./universidad.db"
        # Render utiliza 'postgres://' por defecto; SQLAlchemy 1.4+ requiere 'postgresql://'
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


settings = Settings()
