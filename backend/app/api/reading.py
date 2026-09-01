from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, owned_student
from ..models import AudioAsset, ReadingProgress, Story, StorySentence, Subject, User
from ..schemas import ReadingContentProgressIn
from .audio import ensure_speech

router = APIRouter(prefix="/reading", tags=["reading"])


def enabled_story(db: Session, story_id: str) -> Story:
    story = db.get(Story, story_id)
    subject = db.get(Subject, story.subject_id) if story else None
    if not story or not subject or subject.code != "english" or not subject.enabled:
        raise HTTPException(status_code=404, detail="Story not available")
    return story


@router.get("/stories")
def stories(grade: int | None = None, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Story).join(Subject).where(Subject.code == "english", Subject.enabled.is_(True))
    if grade:
        stmt = stmt.where(Story.grade == grade)
    return [{"id": item.id, "title": item.title, "grade": item.grade, "level": item.level} for item in db.scalars(stmt.order_by(Story.grade, Story.level, Story.title))]


@router.get("/stories/{story_id}")
def story(story_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = enabled_story(db, story_id)
    sentences = db.scalars(select(StorySentence).where(StorySentence.story_id == item.id).order_by(StorySentence.position)).all()
    return {"id": item.id, "title": item.title, "grade": item.grade, "level": item.level, "sentences": [{"id": sentence.id, "position": sentence.position, "text": sentence.text, "translation": sentence.translation, "duration_ms": sentence.duration_ms, "audio_url": f"/api/v1/audio/{sentence.audio_asset_id}" if sentence.audio_asset_id else None} for sentence in sentences]}


@router.post("/story-sentences/{sentence_id}/speech")
async def story_speech(sentence_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sentence = db.get(StorySentence, sentence_id)
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")
    enabled_story(db, sentence.story_id)
    asset = db.get(AudioAsset, sentence.audio_asset_id) if sentence.audio_asset_id else None
    if not asset:
        asset = await ensure_speech(db, sentence.text)
        sentence.audio_asset_id = asset.id
        db.commit()
    return {"audio_id": asset.id, "url": f"/api/v1/audio/{asset.id}"}


@router.put("/{content_kind}/{content_id}/progress")
def save_progress(content_kind: str, content_id: str, payload: ReadingContentProgressIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if content_kind not in {"passage", "story"}:
        raise HTTPException(status_code=400, detail="Unsupported reading content")
    owned_student(db, user, payload.student_id)
    if content_kind == "story":
        enabled_story(db, content_id)
    progress = db.scalar(select(ReadingProgress).where(ReadingProgress.student_id == payload.student_id, ReadingProgress.content_kind == content_kind, ReadingProgress.content_id == content_id))
    if not progress:
        progress = ReadingProgress(student_id=payload.student_id, passage_id=content_id if content_kind == "passage" else None, content_kind=content_kind, content_id=content_id)
        db.add(progress)
    progress.page_id = payload.page_id
    progress.sentence_position = payload.sentence_position
    progress.completed = payload.completed
    progress.completed_at = datetime.utcnow() if payload.completed else None
    db.commit()
    return {"saved": True, "completed_at": progress.completed_at}
