from functools import lru_cache
import json
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
    runtime_config_path: Path = Path("./data/config/ai.env")
    resource_root: Path = Path("./data/resources")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        return value.split(",") if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    path = settings.runtime_config_path
    if path.is_file():
        fields = {
            "AI_PROVIDER": "ai_provider", "DASHSCOPE_API_KEY": "dashscope_api_key",
            "DASHSCOPE_BASE_URL": "dashscope_base_url", "DASHSCOPE_CHAT_MODEL": "dashscope_chat_model",
            "DASHSCOPE_ASR_MODEL": "dashscope_asr_model", "DASHSCOPE_TTS_MODEL": "dashscope_tts_model",
            "DASHSCOPE_TTS_VOICE": "dashscope_tts_voice", "DASHSCOPE_TTS_URL": "dashscope_tts_url",
        }
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw or raw.lstrip().startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            if key.strip() in fields:
                value = value.strip()
                if value.startswith(('"', "'")):
                    try: value = json.loads(value)
                    except Exception: value = value[1:-1]
                setattr(settings, fields[key.strip()], value)
    return settings
