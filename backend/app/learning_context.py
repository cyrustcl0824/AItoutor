from __future__ import annotations

from dataclasses import asdict, dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Course, KnowledgePoint, Lesson, Mastery, Mistake, Student, Subject, Unit
from .schemas import LearningContextIn


@dataclass
class CurrentLearningContext:
    student_id: str
    subject: str
    grade: int
    semester: str | None
    book_id: str | None
    unit_id: str | None
    lesson_id: str | None
    knowledge_point_codes: list[str]
    scenario: str
    difficulty: int
    recent_mistakes: list[str]
    mastery_summary: list[dict]
    available_minutes: int

    def to_dict(self) -> dict:
        return asdict(self)


def build_learning_context(db: Session, student: Student, requested: LearningContextIn | None, session_lesson_id: str | None) -> CurrentLearningContext:
    lesson_id = requested.lesson_id if requested and requested.lesson_id else session_lesson_id
    unit = course = None
    if lesson_id:
        lesson = db.get(Lesson, lesson_id)
        unit = db.get(Unit, lesson.unit_id) if lesson else None
        course = db.get(Course, unit.course_id) if unit else None
        subject = db.get(Subject, course.subject_id) if course else None
        if not lesson or not subject or subject.code != "english" or not subject.enabled or course.grade != student.grade:
            raise HTTPException(status_code=404, detail="Learning context not available for this student")
        if requested and requested.unit_id and requested.unit_id != unit.id:
            raise HTTPException(status_code=400, detail="Lesson does not belong to supplied unit")
        if requested and requested.book_id and requested.book_id != course.id:
            raise HTTPException(status_code=400, detail="Lesson does not belong to supplied book")
    mastery_rows = db.execute(select(Mastery, KnowledgePoint).join(KnowledgePoint).where(Mastery.student_id == student.id).order_by(Mastery.score).limit(8)).all()
    mistakes = db.scalars(select(Mistake).where(Mistake.student_id == student.id, Mistake.resolved.is_(False)).order_by(Mistake.last_seen_at.desc()).limit(5)).all()
    codes = [kp.code for _, kp in mastery_rows]
    difficulty = round(sum(m.difficulty for m, _ in mastery_rows) / len(mastery_rows)) if mastery_rows else 1
    return CurrentLearningContext(
        student_id=student.id,
        subject="english",
        grade=student.grade,
        semester=course.semester if course else None,
        book_id=course.id if course else None,
        unit_id=unit.id if unit else None,
        lesson_id=lesson_id,
        knowledge_point_codes=codes,
        scenario=requested.scenario if requested else "同步巩固",
        difficulty=difficulty,
        recent_mistakes=[item.content for item in mistakes],
        mastery_summary=[{"code": kp.code, "score": mastery.score, "difficulty": mastery.difficulty} for mastery, kp in mastery_rows],
        available_minutes=requested.available_minutes if requested else 15,
    )
