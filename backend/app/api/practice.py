from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, owned_student
from ..models import Attempt, Course, Exercise, LearningSession, Lesson, LessonProgress, Subject, Unit, User
from ..practice import record_answer
from ..schemas import PracticeAnswer, PracticeFinish, PracticeStart

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/start", status_code=201)
def start(payload: PracticeStart, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = owned_student(db, user, payload.student_id)
    lesson = db.get(Lesson, payload.lesson_id)
    english = db.scalar(select(Subject).where(Subject.code == "english", Subject.enabled.is_(True)))
    unit = db.get(Unit, lesson.unit_id) if lesson else None
    course = db.get(Course, unit.course_id) if unit else None
    if not lesson or not english or not course or course.subject_id != english.id or course.grade != student.grade:
        raise HTTPException(status_code=404, detail="English lesson not found")
    session = LearningSession(student_id=payload.student_id, subject_id=english.id, lesson_id=lesson.id, mode="lesson")
    db.add(session)
    db.commit()
    return {"id": session.id, "lesson_id": lesson.id, "started_at": session.started_at}


@router.post("/{session_id}/answers")
def answer(session_id: str, payload: PracticeAnswer, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(LearningSession, session_id)
    if not session or session.ended_at:
        raise HTTPException(status_code=404, detail="Active practice session not found")
    owned_student(db, user, session.student_id)
    exercise = db.get(Exercise, payload.exercise_id)
    if not exercise or exercise.lesson_id != session.lesson_id:
        raise HTTPException(status_code=404, detail="Exercise not found in this lesson")
    correct = record_answer(db, session.student_id, exercise, payload.answer)
    db.commit()
    return {"correct": correct, "answer": exercise.answer, "explanation": exercise.explanation, "score": exercise.score if correct else 0}


@router.post("/finish")
def finish(payload: PracticeFinish, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(LearningSession, payload.session_id)
    if not session or session.ended_at or session.mode != "lesson" or not session.lesson_id:
        raise HTTPException(status_code=404, detail="Active practice session not found")
    owned_student(db, user, session.student_id)
    attempts = db.scalars(select(Attempt).join(Exercise, Attempt.exercise_id == Exercise.id).where(Attempt.student_id == session.student_id, Exercise.lesson_id == session.lesson_id, Attempt.created_at >= session.started_at)).all()
    correct = sum(item.result in {"correct", "correct_after_hint"} for item in attempts)
    accuracy = correct / len(attempts) if attempts else 0.0
    stars = 3 if accuracy >= .9 else 2 if accuracy >= .7 else 1 if attempts else 0
    now = datetime.utcnow()
    progress = db.scalar(select(LessonProgress).where(LessonProgress.student_id == session.student_id, LessonProgress.lesson_id == session.lesson_id))
    if not progress:
        progress = LessonProgress(student_id=session.student_id, lesson_id=session.lesson_id, best_accuracy=0.0, stars=0, completion_count=0, first_completed_at=now)
        db.add(progress)
    progress.best_accuracy = max(progress.best_accuracy, accuracy)
    progress.stars = max(progress.stars, stars)
    progress.completion_count += 1
    progress.last_completed_at = now
    session.ended_at = now
    session.duration_seconds = max(0, int((now - session.started_at).total_seconds()))
    db.commit()
    return {"attempts": len(attempts), "correct": correct, "accuracy": round(accuracy, 3), "stars": stars, "best_accuracy": progress.best_accuracy}
