"""Small compatibility surface for the vendored Hermes education skills."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Exercise, KnowledgePoint, Lesson, Mistake, Student
from .practice import grade_answer


class HermesSkillAdapter:
    def __init__(self, db: Session, student: Student):
        self.db, self.student = db, student

    def curriculum_resolve(self, lesson_id: str) -> dict:
        lesson = self.db.get(Lesson, lesson_id)
        if not lesson:
            return {}
        exercises = self.db.scalars(select(Exercise).where(Exercise.lesson_id == lesson_id)).all()
        return {"lesson_id": lesson.id, "title": lesson.title, "knowledge_point_ids": sorted({e.knowledge_point_id for e in exercises if e.knowledge_point_id})}

    def mistake_query_recent(self, limit: int = 10) -> list[dict]:
        rows = self.db.scalars(select(Mistake).where(Mistake.student_id == self.student.id, Mistake.resolved.is_(False)).order_by(Mistake.last_seen_at.desc()).limit(limit)).all()
        return [{"id": row.id, "content": row.content, "box": row.srs_box} for row in rows]

    def practice_grade_answers(self, exercise_id: str, answer: str) -> bool:
        exercise = self.db.get(Exercise, exercise_id)
        return bool(exercise and grade_answer(exercise, answer))

    def plan_generate(self, available_minutes: int) -> dict:
        return {"available_minutes": available_minutes, "steps": ["review_due_mistakes", "practice_current_lesson", "short_recap"]}

    def memory_write(self, *_args, **_kwargs) -> None:
        raise RuntimeError("Hermes skills cannot write learning state directly; use the deterministic learning services")
