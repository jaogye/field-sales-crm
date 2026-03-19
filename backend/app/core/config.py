"""
Application configuration — loads from .env file.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str = ""

    # Database — /data is the Fly.io persistent volume mount point
    database_path: str = "/data/crm.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Audio storage
    audio_storage_path: str = "/data/audios"

    # AI Models
    whisper_model: str = "whisper-1"
    gpt_model: str = "gpt-4o-mini"

    # Transcription
    transcription_language: str = "auto"  # auto-detect Spanish/English
    max_audio_size_mb: int = 50

    # Security
    secret_key: str = "change-this-to-a-random-string-in-production"
    access_token_expire_minutes: int = 43200  # 30 days (mobile-friendly)

    # CORS — comma-separated origins or JSON array in env
    cors_origins: list[str] = ["http://localhost:8501", "http://localhost:3000"]

    # Dashboard authentication (empty = no gate)
    dashboard_password: str = ""

    # Account lockout
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def audio_dir(self) -> Path:
        path = Path(self.audio_storage_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
