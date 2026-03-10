"""
Application configuration — loads from .env file.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""

    # Database
    database_path: str = "C:/ventas/crm.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Audio storage
    audio_storage_path: str = "C:/ventas/audios"

    # AI Models
    whisper_model: str = "whisper-1"
    gpt_model: str = "gpt-4o-mini"

    # Transcription
    transcription_language: str = "auto"  # auto-detect Spanish/English
    max_audio_size_mb: int = 50

    # Security
    secret_key: str = "change-this-to-a-random-string-in-production"
    api_key_header: str = "X-API-Key"

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
