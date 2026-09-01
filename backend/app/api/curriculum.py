from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, owned_student
from ..models import Course, Exercise, KnowledgePoint, Lesson, LessonProgress, Subject, Unit, User

router = APIRouter(tags=["curriculum"])


@router.get("/subjects")
def subjects(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": s.id, "code": s.code, "name": s.name, "enabled": s.enabled} for s in db.scalars(select(Subject).order_by(Subject.code))]


@router.get("/subjects/{code}")
def subject(code: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Subject).where(Subject.code == code))
    if not item:
        raise HTTPException(status_code=404, detail="Subject not found")
    return {"id": item.id, "code": item.code, "name": item.name, "enabled": item.enabled}


@router.get("/curriculum/courses")
def courses(grade: int | None = None, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    english = db.scalar(select(Subject).where(Subject.code == "english", Subject.enabled.is_(True)))
    stmt = select(Course).where(Course.subject_id == english.id)
    if grade:
        stmt = stmt.where(Course.grade == grade)
    return [{"id": c.id, "name": c.name, "grade": c.grade, "semester": c.semester} for c in db.scalars(stmt.order_by(Course.grade, Course.semester))]


@router.get("/curriculum/courses/{course_id}/units")
def units(course_id: str, student_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    english = db.get(Subject, course.subject_id) if course else None
    if not course or not english or english.code != "english" or not english.enabled:
        raise HTTPException(status_code=404, detail="Course not found")
    if student_id:
        owned_student(db, user, student_id)
    return [{"id": u.id, "title": u.title, "position": u.position} for u in db.scalars(select(Unit).where(Unit.course_id == course_id).order_by(Unit.position))]


@router.get("/curriculum/units/{unit_id}/lessons")
def lessons(unit_id: str, student_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if student_id:
        owned_student(db, user, student_id)
    items = db.scalars(select(Lesson).where(Lesson.unit_id == unit_id).order_by(Lesson.position)).all()
    progress = {}
    if student_id and items:
        progress = {p.lesson_id: p for p in db.scalars(select(LessonProgress).where(LessonProgress.student_id == student_id, LessonProgress.lesson_id.in_([item.id for item in items])))}
    return [{"id": item.id, "title": item.title, "position": item.position, "progress": ({"best_accuracy": progress[item.id].best_accuracy, "stars": progress[item.id].stars, "completion_count": progress[item.id].completion_count} if item.id in progress else None)} for item in items]


@router.get("/curriculum/lessons/{lesson_id}")
def lesson_detail(lesson_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    unit = db.get(Unit, lesson.unit_id) if lesson else None
    course = db.get(Course, unit.course_id) if unit else None
    subject = db.get(Subject, course.subject_id) if course else None
    if not lesson or not subject or subject.code != "english" or not subject.enabled:
        raise HTTPException(status_code=404, detail="Lesson not found")
    exercises = db.scalars(select(Exercise).where(Exercise.lesson_id == lesson_id).order_by(Exercise.external_id)).all()
    points = {kp.id: kp for kp in db.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_([e.knowledge_point_id for e in exercises if e.knowledge_point_id])))} if exercises else {}
    return {"id": lesson.id, "title": lesson.title, "position": lesson.position, "knowledge_cards": [{"code": kp.code, "name": kp.name, "description": kp.metadata_json.get("description", "")} for kp in points.values()], "exercises": [{"id": e.id, "type": e.kind, "prompt": e.prompt, "options": e.options, "difficulty": e.difficulty, "score": e.score} for e in exercises]}
