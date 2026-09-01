from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, owned_student
from ..models import (AudioAsset, Course, Lesson, LessonPageLink, Passage, PassageSentence, ReadingProgress,
                      Subject, TextbookEdition, TextbookPage, Unit, User)
from .audio import ensure_speech
from ..schemas import ReadingProgressIn

router = APIRouter(prefix="/textbooks", tags=["textbooks"])


def enabled_edition(db: Session, edition_id: str) -> TextbookEdition:
    edition = db.get(TextbookEdition, edition_id)
    subject = db.get(Subject, edition.subject_id) if edition else None
    if not edition or not subject or not subject.enabled:
        raise HTTPException(status_code=404, detail="Textbook not available")
    return edition


@router.get("")
def list_textbooks(grade: int | None = None, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(TextbookEdition).join(Subject).where(Subject.enabled.is_(True))
    if grade:
        stmt = stmt.where(TextbookEdition.grade == grade)
    return [{"id": e.id, "title": e.title, "publisher": e.publisher, "grade": e.grade, "semester": e.semester} for e in db.scalars(stmt)]


@router.get("/{edition_id}/pages")
def list_pages(edition_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enabled_edition(db, edition_id)
    pages = db.scalars(select(TextbookPage).where(TextbookPage.edition_id == edition_id).order_by(TextbookPage.position)).all()
    return [{"id": p.id, "position": p.position, "printed_page": p.printed_page, "image_url": f"/api/v1/textbooks/pages/{p.id}/image", "thumbnail_url": f"/api/v1/textbooks/pages/{p.id}/thumbnail"} for p in pages]


@router.get("/{edition_id}/contents")
def contents(edition_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    edition = enabled_edition(db, edition_id)
    course = db.scalar(select(Course).where(Course.subject_id == edition.subject_id, Course.grade == edition.grade, Course.semester == edition.semester))
    if not course:
        return []
    units = db.scalars(select(Unit).where(Unit.course_id == course.id).order_by(Unit.position)).all()
    return [{"id": unit.id, "title": unit.title, "position": unit.position, "lessons": [{"id": lesson.id, "title": lesson.title, "position": lesson.position} for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id).order_by(Lesson.position))]} for unit in units]


def page_file(db: Session, page_id: str, thumbnail: bool):
    page = db.get(TextbookPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    enabled_edition(db, page.edition_id)
    path = Path(page.thumbnail_path if thumbnail else page.web_path).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Page asset missing")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "private, max-age=604800", "ETag": page.sha256})


@router.get("/pages/{page_id}/image")
def image(page_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return page_file(db, page_id, False)


@router.get("/pages/{page_id}/thumbnail")
def thumbnail(page_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return page_file(db, page_id, True)


@router.get("/lessons/{lesson_id}/reading")
def lesson_reading(lesson_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    unit = db.get(Unit, lesson.unit_id)
    course = db.get(Course, unit.course_id)
    subject = db.get(Subject, course.subject_id)
    if not subject.enabled:
        raise HTTPException(status_code=404, detail="Lesson not available")
    link = db.scalar(select(LessonPageLink).where(LessonPageLink.lesson_id == lesson_id))
    passage = db.scalar(select(Passage).where(Passage.lesson_id == lesson_id))
    sentences = db.scalars(select(PassageSentence).where(PassageSentence.passage_id == passage.id).order_by(PassageSentence.position)).all() if passage else []
    page_ids = []
    if link:
        start, end = db.get(TextbookPage, link.start_page_id), db.get(TextbookPage, link.end_page_id)
        if start and end and start.edition_id == end.edition_id:
            page_ids = list(db.scalars(select(TextbookPage.id).where(TextbookPage.edition_id == start.edition_id, TextbookPage.position.between(start.position, end.position)).order_by(TextbookPage.position)))
    return {
        "lesson": {"id": lesson.id, "title": lesson.title},
        "page_ids": page_ids,
        "passage": {"id": passage.id, "title": passage.title} if passage else None,
        "sentences": [{"id": s.id, "position": s.position, "text": s.text, "page_id": s.page_id, "duration_ms": s.duration_ms, "audio_url": f"/api/v1/audio/{s.audio_asset_id}" if s.audio_asset_id else None} for s in sentences],
    }


@router.post("/sentences/{sentence_id}/speech")
async def sentence_speech(sentence_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sentence = db.get(PassageSentence, sentence_id)
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")
    passage = db.get(Passage, sentence.passage_id)
    lesson = db.get(Lesson, passage.lesson_id)
    unit = db.get(Unit, lesson.unit_id)
    course = db.get(Course, unit.course_id)
    subject = db.get(Subject, course.subject_id)
    if not subject.enabled:
        raise HTTPException(status_code=404, detail="Sentence not available")
    asset = db.get(AudioAsset, sentence.audio_asset_id) if sentence.audio_asset_id else None
    if not asset:
        asset = await ensure_speech(db, sentence.text)
        sentence.audio_asset_id = asset.id
        db.commit()
    return {"audio_id": asset.id, "url": f"/api/v1/audio/{asset.id}"}


@router.put("/passages/{passage_id}/progress")
def save_progress(passage_id: str, payload: ReadingProgressIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_student(db, user, payload.student_id)
    passage = db.get(Passage, passage_id)
    if not passage:
        raise HTTPException(status_code=404, detail="Passage not found")
    progress = db.scalar(select(ReadingProgress).where(ReadingProgress.student_id == payload.student_id, ReadingProgress.passage_id == passage_id))
    if not progress:
        progress = ReadingProgress(student_id=payload.student_id, passage_id=passage_id, content_kind="passage", content_id=passage_id)
        db.add(progress)
    progress.page_id = payload.page_id
    progress.sentence_position = payload.sentence_position
    progress.completed = payload.completed
    db.commit()
    return {"saved": True}
