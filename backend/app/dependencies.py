from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import Student, User
from .security import current_user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return current_user(request, db)


def owned_student(db: Session, user: User, student_id: str) -> Student:
    student = db.get(Student, student_id)
    if not student or student.family_id != user.family_id or not student.active:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student not found")
    return student

