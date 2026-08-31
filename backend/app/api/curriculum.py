from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Course, Lesson, Subject, TextbookEdition, Unit, User

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
def units(course_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": u.id, "title": u.title, "position": u.position} for u in db.scalars(select(Unit).where(Unit.course_id == course_id).order_by(Unit.position))]


@router.get("/curriculum/units/{unit_id}/lessons")
def lessons(unit_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": lesson.id, "title": lesson.title, "position": lesson.position} for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit_id).order_by(Lesson.position))]

