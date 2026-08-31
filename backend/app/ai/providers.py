from __future__ import annotations

import base64
import io
import json
import math
import struct
import wave
from abc import ABC, abstractmethod

import httpx

from ..config import Settings, get_settings
from ..schemas import TutorDecision


class ProviderError(RuntimeError):
    pass


class ChatProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], tier: str, response_schema: dict) -> dict: ...


class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, mime_type: str, language: str | None) -> str: ...


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str, output_format: str) -> bytes: ...


class VisionProvider(ABC):
    async def analyze(self, image: bytes) -> dict:
        raise ProviderError("Vision is not enabled in V1")


class MockProvider(ChatProvider, ASRProvider, TTSProvider):
    async def complete(self, messages: list[dict], tier: str, response_schema: dict) -> dict:
        child_text = messages[-1]["content"].strip()
        lower = child_text.lower()
        if "two cat" in lower:
            return TutorDecision(reply='Almost! You have two, so should we say "cat" or "cats"?', intent="grammar", knowledge_point_code="plural_nouns", result="incorrect", hint_count=1).model_dump()
        if lower in {"cats", "cats!"}:
            return TutorDecision(reply="Yes! I have two cats! Great job!", intent="grammar", knowledge_point_code="plural_nouns", result="correct_after_hint", hint_count=1).model_dump()
        return TutorDecision(reply=f"Great try! Can you tell me one more thing about {child_text[:40]}?", result="partially_correct").model_dump()

    async def transcribe(self, audio: bytes, mime_type: str, language: str | None) -> str:
        return "I like English."

    async def synthesize(self, text: str, voice: str, output_format: str) -> bytes:
        rate, seconds = 16000, max(0.4, min(3.0, len(text) * 0.045))
        out = io.BytesIO()
        with wave.open(out, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            frames = bytearray()
            for i in range(int(rate * seconds)):
                frames.extend(struct.pack("<h", int(900 * math.sin(2 * math.pi * 440 * i / rate))))
            wav.writeframes(frames)
        return out.getvalue()


class DashScopeProvider(ChatProvider, ASRProvider, TTSProvider):
    def __init__(self, settings: Settings):
        if not settings.dashscope_api_key:
            raise ProviderError("DASHSCOPE_API_KEY is required")
        self.settings = settings
        self.headers = {"Authorization": f"Bearer {settings.dashscope_api_key}", "Content-Type": "application/json"}

    async def _chat_request(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.settings.dashscope_base_url.rstrip('/')}/chat/completions", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def complete(self, messages: list[dict], tier: str, response_schema: dict) -> dict:
        payload = {"model": self.settings.dashscope_chat_model, "messages": messages, "response_format": {"type": "json_object"}, "temperature": 0.3}
        try:
            body = await self._chat_request(payload)
            return json.loads(body["choices"][0]["message"]["content"])
        except Exception as exc:
            raise ProviderError("DashScope chat request failed") from exc

    async def transcribe(self, audio: bytes, mime_type: str, language: str | None) -> str:
        data_uri = f"data:{mime_type};base64,{base64.b64encode(audio).decode()}"
        payload = {
            "model": self.settings.dashscope_asr_model,
            "messages": [{"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": data_uri}}]}],
            "stream": False,
            "asr_options": {"enable_itn": True, **({"language": language} if language else {})},
        }
        try:
            body = await self._chat_request(payload)
            return body["choices"][0]["message"]["content"]
        except Exception as exc:
            raise ProviderError("DashScope ASR request failed") from exc

    async def synthesize(self, text: str, voice: str, output_format: str) -> bytes:
        payload = {"model": self.settings.dashscope_tts_model, "input": {"text": text, "voice": voice or self.settings.dashscope_tts_voice, "format": output_format, "sample_rate": 24000}}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(self.settings.dashscope_tts_url, headers=self.headers, json=payload)
                response.raise_for_status()
                body = response.json()
                audio_url = body.get("output", {}).get("audio", {}).get("url") or body.get("output", {}).get("audio_url")
                if not audio_url:
                    raise ProviderError("TTS response did not include audio URL")
                audio_response = await client.get(audio_url)
                audio_response.raise_for_status()
                return audio_response.content
        except Exception as exc:
            raise ProviderError("DashScope TTS request failed") from exc


def get_provider():
    settings = get_settings()
    return DashScopeProvider(settings) if settings.ai_provider == "dashscope" else MockProvider()

