from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Attempt, KnowledgePoint, Mastery, Mistake, ReviewTask, Subject
from .schemas import TutorDecision

SCORE_DELTAS = {"correct": 0.10, "correct_after_hint": 0.06, "partially_correct": 0.02, "incorrect": -0.08, "skipped": -0.03}


def update_learning_state(db: Session, student_id: str, answer: str, decision: TutorDecision) -> None:
    if not decision.knowledge_point_code or not decision.result:
        return
    kp = db.scalar(select(KnowledgePoint).where(KnowledgePoint.code == decision.knowledge_point_code))
    if not kp:
        english = db.scalar(select(Subject).where(Subject.code == "english"))
        kp = KnowledgePoint(subject_id=english.id, code=decision.knowledge_point_code, name=decision.knowledge_point_code.replace("_", " ").title())
        db.add(kp)
        db.flush()
    mastery = db.scalar(select(Mastery).where(Mastery.student_id == student_id, Mastery.knowledge_point_id == kp.id))
    if not mastery:
        mastery = Mastery(student_id=student_id, knowledge_point_id=kp.id)
        db.add(mastery)
        db.flush()
    mastery.attempt_count += 1
    is_correct = decision.result in {"correct", "correct_after_hint"}
    mastery.correct_count += int(is_correct)
    mastery.correct_streak = mastery.correct_streak + 1 if is_correct else 0
    mastery.difficult_streak = 0 if is_correct else mastery.difficult_streak + 1
    mastery.score = min(1.0, max(0.0, mastery.score + SCORE_DELTAS[decision.result]))
    mastery.confidence = min(1.0, mastery.confidence + 0.05)
    if mastery.correct_streak >= 3:
        mastery.difficulty = min(5, mastery.difficulty + 1)
        mastery.correct_streak = 0
    elif mastery.difficult_streak >= 2:
        mastery.difficulty = max(1, mastery.difficulty - 1)
        mastery.difficult_streak = 0
    mastery.last_practiced_at = datetime.utcnow()
    mastery.next_review_at = datetime.utcnow() + timedelta(days=1 if not is_correct else max(1, int(1 + mastery.score * 6)))
    db.add(Attempt(student_id=student_id, knowledge_point_id=kp.id, answer=answer, result=decision.result, hint_count=decision.hint_count))
    if not is_correct:
        mistake = db.scalar(select(Mistake).where(Mistake.student_id == student_id, Mistake.knowledge_point_id == kp.id, Mistake.content == answer))
        if mistake:
            mistake.occurrence_count += 1
            mistake.last_seen_at = datetime.utcnow()
        else:
            db.add(Mistake(student_id=student_id, subject_id=kp.subject_id, knowledge_point_id=kp.id, content=answer))
    pending = db.scalar(select(ReviewTask).where(ReviewTask.student_id == student_id, ReviewTask.knowledge_point_id == kp.id, ReviewTask.status == "pending"))
    if pending:
        pending.due_at = mastery.next_review_at
    else:
        db.add(ReviewTask(student_id=student_id, knowledge_point_id=kp.id, due_at=mastery.next_review_at))
