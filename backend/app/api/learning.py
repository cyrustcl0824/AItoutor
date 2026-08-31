from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, owned_student
from ..models import Attempt, KnowledgePoint, LearningSession, Mastery, Mistake, ReviewTask, User

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/{student_id}/progress")
def progress(student_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_student(db, user, student_id)
    rows = db.execute(select(Mastery, KnowledgePoint).join(KnowledgePoint).where(Mastery.student_id == student_id)).all()
    return [{"knowledge_point": kp.name, "code": kp.code, "score": m.score, "confidence": m.confidence, "difficulty": m.difficulty, "attempt_count": m.attempt_count, "next_review_at": m.next_review_at} for m, kp in rows]


@router.get("/{student_id}/mistakes")
def mistakes(student_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_student(db, user, student_id)
    items = db.scalars(select(Mistake).where(Mistake.student_id == student_id, Mistake.resolved.is_(False)).order_by(Mistake.last_seen_at.desc())).all()
    return [{"id": m.id, "content": m.content, "type": m.mistake_type, "occurrence_count": m.occurrence_count, "last_seen_at": m.last_seen_at} for m in items]


@router.get("/{student_id}/review/today")
def today_review(student_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_student(db, user, student_id)
    tasks = db.execute(select(ReviewTask, KnowledgePoint).join(KnowledgePoint).where(ReviewTask.student_id == student_id, ReviewTask.status == "pending", ReviewTask.due_at <= datetime.utcnow()).order_by(ReviewTask.due_at).limit(10)).all()
    return [{"id": task.id, "knowledge_point": kp.name, "code": kp.code, "due_at": task.due_at} for task, kp in tasks]


@router.get("/{student_id}/weekly-report")
def weekly_report(student_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_student(db, user, student_id)
    since = datetime.utcnow() - timedelta(days=7)
    attempt_count = db.scalar(select(func.count(Attempt.id)).where(Attempt.student_id == student_id, Attempt.created_at >= since)) or 0
    correct_count = db.scalar(select(func.count(Attempt.id)).where(Attempt.student_id == student_id, Attempt.created_at >= since, Attempt.result.in_(["correct", "correct_after_hint"]))) or 0
    seconds = db.scalar(select(func.sum(LearningSession.duration_seconds)).where(LearningSession.student_id == student_id, LearningSession.started_at >= since)) or 0
    weak = db.execute(select(Mastery, KnowledgePoint).join(KnowledgePoint).where(Mastery.student_id == student_id).order_by(Mastery.score).limit(5)).all()
    return {"period_days": 7, "attempts": attempt_count, "correct": correct_count, "accuracy": round(correct_count / attempt_count, 3) if attempt_count else 0, "learning_seconds": seconds, "weak_points": [{"name": kp.name, "score": mastery.score} for mastery, kp in weak]}

