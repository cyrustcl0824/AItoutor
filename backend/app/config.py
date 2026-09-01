from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "development-only-secret-change-me"
    database_url: str = "sqlite:///./data/tutor.db"
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    ai_provider: str = "mock"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_chat_model: str = "qwen-plus"
    dashscope_asr_model: str = "qwen3-asr-flash"
    dashscope_tts_model: str = "cosyvoice-v3-flash"
    dashscope_tts_voice: str = "longanyang"
    dashscope_tts_url: str = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
    textbook_root: Path = Path("./data/textbook-pages")
    audio_cache_root: Path = Path("./data/audio-cache")
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    max_audio_bytes: int = 10 * 1024 * 1024

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        return value.split(",") if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
