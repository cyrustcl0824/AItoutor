from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Attempt, Exercise, KnowledgePoint, Mastery, Mistake, ReviewTask


def normalize_answer(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def grade_answer(exercise: Exercise, submitted: str) -> bool:
    expected = exercise.answer
    if exercise.kind in {"choice", "true_false", "fill_blank", "fill_blank_text", "short_answer", "word_order"}:
        accepted = [part for part in expected.split("||") if part]
        return normalize_answer(submitted) in {normalize_answer(item) for item in accepted}
    return normalize_answer(submitted) == normalize_answer(expected)


def record_answer(db: Session, student_id: str, exercise: Exercise, submitted: str) -> bool:
    correct = grade_answer(exercise, submitted)
    result = "correct" if correct else "incorrect"
    db.add(Attempt(student_id=student_id, exercise_id=exercise.id, knowledge_point_id=exercise.knowledge_point_id, answer=submitted, result=result))
    now = datetime.utcnow()

    if exercise.knowledge_point_id:
        mastery = db.scalar(select(Mastery).where(Mastery.student_id == student_id, Mastery.knowledge_point_id == exercise.knowledge_point_id))
        if not mastery:
            mastery = Mastery(student_id=student_id, knowledge_point_id=exercise.knowledge_point_id)
            db.add(mastery)
            db.flush()
        mastery.attempt_count += 1
        mastery.correct_count += int(correct)
        mastery.correct_streak = mastery.correct_streak + 1 if correct else 0
        mastery.difficult_streak = 0 if correct else mastery.difficult_streak + 1
        mastery.score = min(1.0, max(0.0, mastery.score + (0.1 if correct else -0.08)))
        mastery.confidence = min(1.0, mastery.confidence + 0.05)
        if mastery.correct_streak >= 3:
            mastery.difficulty = min(5, mastery.difficulty + 1)
            mastery.correct_streak = 0
        elif mastery.difficult_streak >= 2:
            mastery.difficulty = max(1, mastery.difficulty - 1)
            mastery.difficult_streak = 0
        mastery.last_practiced_at = now
        mastery.next_review_at = now + timedelta(days=7 if correct else 1)
        task = db.scalar(select(ReviewTask).where(ReviewTask.student_id == student_id, ReviewTask.knowledge_point_id == exercise.knowledge_point_id, ReviewTask.status == "pending"))
        if task:
            task.due_at = mastery.next_review_at
        else:
            db.add(ReviewTask(student_id=student_id, knowledge_point_id=exercise.knowledge_point_id, due_at=mastery.next_review_at))

    mistake = db.scalar(select(Mistake).where(Mistake.student_id == student_id, Mistake.exercise_id == exercise.id))
    if correct:
        return True
    if mistake:
        mistake.occurrence_count += 1
        mistake.last_seen_at = now
        mistake.resolved = False
        mistake.graduated = False
        mistake.srs_box = 1
        mistake.review_correct_count = 0
        mistake.next_review_at = now
    else:
        kp = db.get(KnowledgePoint, exercise.knowledge_point_id) if exercise.knowledge_point_id else None
        subject_id = kp.subject_id if kp else db.execute(select(KnowledgePoint.subject_id).limit(1)).scalar_one_or_none()
        if not subject_id:
            from .models import Subject
            subject_id = db.scalar(select(Subject.id).where(Subject.code == "english"))
        db.add(Mistake(student_id=student_id, subject_id=subject_id, exercise_id=exercise.id, knowledge_point_id=exercise.knowledge_point_id, content=exercise.prompt, next_review_at=now))
    return False


def review_mistake(mistake: Mistake, correct: bool) -> None:
    now = datetime.utcnow()
    mistake.last_reviewed_at = now
    if correct:
        mistake.srs_box = min(3, mistake.srs_box + 1)
        mistake.review_correct_count += 1
        delay = {1: 1, 2: 3, 3: 7}[mistake.srs_box]
        mistake.graduated = mistake.srs_box >= 3 and mistake.review_correct_count >= 2
        mistake.resolved = mistake.graduated
        mistake.next_review_at = now + timedelta(days=delay)
    else:
        mistake.srs_box = 1
        mistake.review_correct_count = 0
        mistake.graduated = False
        mistake.resolved = False
        mistake.next_review_at = now
