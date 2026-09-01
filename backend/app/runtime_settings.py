from __future__ import annotations

import json
import os
from pathlib import Path

from .config import get_settings

KEYS = {
    "ai_provider": "AI_PROVIDER", "dashscope_api_key": "DASHSCOPE_API_KEY",
    "dashscope_base_url": "DASHSCOPE_BASE_URL", "dashscope_chat_model": "DASHSCOPE_CHAT_MODEL",
    "dashscope_asr_model": "DASHSCOPE_ASR_MODEL", "dashscope_tts_model": "DASHSCOPE_TTS_MODEL",
    "dashscope_tts_voice": "DASHSCOPE_TTS_VOICE", "dashscope_tts_url": "DASHSCOPE_TTS_URL",
}


def masked_settings() -> dict:
    settings = get_settings()
    key = settings.dashscope_api_key
    return {
        "provider": settings.ai_provider,
        "api_key_configured": bool(key),
        "api_key_hint": f"****{key[-4:]}" if len(key) >= 4 else ("****" if key else ""),
        "base_url": settings.dashscope_base_url,
        "chat_model": settings.dashscope_chat_model,
        "asr_model": settings.dashscope_asr_model,
        "tts_model": settings.dashscope_tts_model,
        "tts_voice": settings.dashscope_tts_voice,
        "tts_url": settings.dashscope_tts_url,
    }


def update_runtime_settings(values: dict, api_key: str | None, clear_api_key: bool) -> list[str]:
    current = get_settings()
    path = current.runtime_config_path
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    comments = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1); existing[key.strip()] = value.strip()
            elif line: comments.append(line)
    changed = []
    mapping = {
        "provider": "AI_PROVIDER", "base_url": "DASHSCOPE_BASE_URL", "chat_model": "DASHSCOPE_CHAT_MODEL",
        "asr_model": "DASHSCOPE_ASR_MODEL", "tts_model": "DASHSCOPE_TTS_MODEL",
        "tts_voice": "DASHSCOPE_TTS_VOICE", "tts_url": "DASHSCOPE_TTS_URL",
    }
    for field, env_key in mapping.items():
        value = values.get(field)
        if value is not None:
            existing[env_key] = json.dumps(value, ensure_ascii=False)
            changed.append(field)
    if api_key is not None:
        existing["DASHSCOPE_API_KEY"] = json.dumps(api_key)
        changed.append("api_key")
    elif clear_api_key:
        existing["DASHSCOPE_API_KEY"] = '""'
        changed.append("api_key")
    body = "\n".join(comments + [f"{key}={value}" for key, value in existing.items()]) + "\n"
    temp = path.with_suffix(".tmp")
    temp.write_text(body, encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(path)
    get_settings.cache_clear()
    return sorted(set(changed))
