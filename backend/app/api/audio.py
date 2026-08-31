import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.providers import ProviderError, get_provider
from ..config import get_settings
from ..database import get_db
from ..dependencies import get_current_user
from ..models import AudioAsset, User

router = APIRouter(prefix="/audio", tags=["audio"])
ALLOWED_AUDIO = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/webm", "audio/ogg", "audio/mp4"}


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("en"), _: User = Depends(get_current_user)):
    if file.content_type not in ALLOWED_AUDIO:
        raise HTTPException(status_code=415, detail="Unsupported audio type")
    data = await file.read(get_settings().max_audio_bytes + 1)
    if not data or len(data) > get_settings().max_audio_bytes:
        raise HTTPException(status_code=413, detail="Audio must be between 1 byte and 10 MB")
    try:
        text = await get_provider().transcribe(data, file.content_type, language)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="Speech recognition is temporarily unavailable") from exc
    return {"text": text, "language": language}


async def ensure_speech(db: Session, text: str, voice: str = "Emma") -> AudioAsset:
    settings = get_settings()
    cache_key = hashlib.sha256(f"{settings.ai_provider}|{voice}|wav|{text}".encode()).hexdigest()
    asset = db.scalar(select(AudioAsset).where(AudioAsset.cache_key == cache_key))
    if asset and Path(asset.file_path).is_file():
        return asset
    audio = await get_provider().synthesize(text, settings.dashscope_tts_voice if voice == "Emma" else voice, "wav")
    settings.audio_cache_root.mkdir(parents=True, exist_ok=True)
    path = settings.audio_cache_root / f"{cache_key}.wav"
    path.write_bytes(audio)
    asset = AudioAsset(cache_key=cache_key, provider=settings.ai_provider, voice=voice, mime_type="audio/wav", file_path=str(path))
    db.add(asset)
    db.commit()
    return asset


@router.post("/speech")
async def speech(text: str = Form(..., min_length=1, max_length=2000), voice: str = Form("Emma"), _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        asset = await ensure_speech(db, text, voice)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="Speech synthesis is temporarily unavailable") from exc
    return {"audio_id": asset.id, "url": f"/api/v1/audio/{asset.id}"}


@router.get("/{audio_id}")
def get_audio(audio_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.get(AudioAsset, audio_id)
    if not asset or not Path(asset.file_path).is_file():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(asset.file_path, media_type=asset.mime_type, headers={"Cache-Control": "private, max-age=86400", "ETag": asset.cache_key})

