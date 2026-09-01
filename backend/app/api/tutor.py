from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, owned_student
from ..models import ConversationSession, Course, LearningSession, Lesson, Subject, Unit, User
from ..learning_context import build_learning_context
from ..schemas import SessionStart, TutorDecision, TutorMessage
from ..schemas import LearningContextIn
from ..tutor import handle_message
from ..ai.providers import ProviderError, get_provider
from .audio import ALLOWED_AUDIO, ensure_speech
from ..config import get_settings

router = APIRouter(tags=["tutor"])


@router.post("/sessions", status_code=201)
def start_session(payload: SessionStart, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = owned_student(db, user, payload.student_id)
    english = db.scalar(select(Subject).where(Subject.code == "english", Subject.enabled.is_(True)))
    if not english:
        raise HTTPException(status_code=404, detail="English is disabled")
    lesson = db.get(Lesson, payload.lesson_id) if payload.lesson_id else None
    if payload.lesson_id:
        unit = db.get(Unit, lesson.unit_id) if lesson else None
        course = db.get(Course, unit.course_id) if unit else None
        if not lesson or not course or course.subject_id != english.id or course.grade != student.grade:
            raise HTTPException(status_code=404, detail="Lesson not available for this student")
    session = LearningSession(student_id=student.id, subject_id=english.id, lesson_id=lesson.id if lesson else None, mode=payload.mode)
    db.add(session)
    db.flush()
    conversation = ConversationSession(learning_session_id=session.id)
    db.add(conversation)
    db.commit()
    return {"id": session.id, "conversation_id": conversation.id, "mode": session.mode, "started_at": session.started_at}


@router.post("/sessions/{session_id}/end")
def end_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(LearningSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    owned_student(db, user, session.student_id)
    session.ended_at = datetime.utcnow()
    session.duration_seconds = max(0, int((session.ended_at - session.started_at).total_seconds()))
    db.commit()
    return {"id": session.id, "duration_seconds": session.duration_seconds}


@router.post("/tutor/message", response_model=TutorDecision)
async def tutor_message(payload: TutorMessage, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(LearningSession, payload.session_id)
    if not session or session.ended_at:
        raise HTTPException(status_code=404, detail="Active session not found")
    student = owned_student(db, user, session.student_id)
    context = build_learning_context(db, student, payload.learning_context, session.lesson_id)
    return await handle_message(db, session, student, payload.text, context)


@router.post("/tutor/voice-turn")
async def tutor_voice_turn(
    session_id: str = Form(...), audio: UploadFile = File(...), language: str = Form("en"),
    learning_context: str | None = Form(None), user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    session = db.get(LearningSession, session_id)
    if not session or session.ended_at:
        raise HTTPException(status_code=404, detail="Active session not found")
    student = owned_student(db, user, session.student_id)
    if audio.content_type not in ALLOWED_AUDIO:
        raise HTTPException(status_code=415, detail="Unsupported audio type")
    data = await audio.read(get_settings().max_audio_bytes + 1)
    if not data or len(data) > get_settings().max_audio_bytes:
        raise HTTPException(status_code=413, detail="Audio must be between 1 byte and 10 MB")
    requested = None
    if learning_context:
        try: requested = LearningContextIn.model_validate_json(learning_context)
        except Exception as exc: raise HTTPException(status_code=422, detail="Invalid learning context") from exc
    context = build_learning_context(db, student, requested, session.lesson_id)
    try:
        transcript = (await get_provider().transcribe(data, audio.content_type, language)).strip()
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="Speech recognition is temporarily unavailable") from exc
    if not transcript:
        raise HTTPException(status_code=422, detail="No recognizable speech")
    decision = await handle_message(db, session, student, transcript, context)
    audio_result, audio_error = None, None
    try:
        asset = await ensure_speech(db, decision.reply)
        audio_result = {"id": asset.id, "url": f"/api/v1/audio/{asset.id}", "duration_ms": asset.duration_ms}
    except Exception:
        audio_error = {"code": "tts_unavailable", "message": "Voice playback is temporarily unavailable"}
    return {"transcript": transcript, "decision": decision.model_dump(), "audio": audio_result, "audio_error": audio_error}
