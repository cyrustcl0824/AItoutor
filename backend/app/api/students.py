from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, owned_student
from ..models import Student, User
from ..schemas import StudentCreate, StudentOut, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=list[StudentOut])
def list_students(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Student).where(Student.family_id == user.family_id, Student.active.is_(True))).all()


@router.post("", response_model=StudentOut, status_code=201)
def create_student(payload: StudentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = Student(family_id=user.family_id, **payload.model_dump())
    db.add(student)
    db.commit()
    return student


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: str, payload: StudentUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = owned_student(db, user, student_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, key, value)
    db.commit()
    return student

