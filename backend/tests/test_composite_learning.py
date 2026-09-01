from sqlalchemy import select

from app.database import SessionLocal
from app.models import Course, Exercise, KnowledgePoint, Lesson, LessonProgress, Mistake, Subject, Unit


def seed_lesson():
    with SessionLocal() as db:
        english = db.scalar(select(Subject).where(Subject.code == "english"))
        course = Course(subject_id=english.id, external_id="test-course", name="PEP 三年级", grade=3, semester="上册")
        db.add(course); db.flush()
        unit = Unit(course_id=course.id, external_id="test-unit", title="Unit 1", position=1)
        db.add(unit); db.flush()
        lesson = Lesson(unit_id=unit.id, external_id="test-lesson", title="Hello", position=1)
        db.add(lesson); db.flush()
        kp = KnowledgePoint(subject_id=english.id, code="test_greeting", name="Greeting")
        db.add(kp); db.flush()
        exercise = Exercise(lesson_id=lesson.id, knowledge_point_id=kp.id, external_id="test-exercise", prompt="Say hello", answer="Hello", kind="short_answer", explanation="Hello is a greeting.")
        db.add(exercise); db.commit()
        return lesson.id, exercise.id


def test_practice_updates_attempt_mistake_srs_and_progress(client, student):
    lesson_id, exercise_id = seed_lesson()
    started = client.post("/api/v1/practice/start", json={"student_id": student["id"], "lesson_id": lesson_id})
    assert started.status_code == 201
    session_id = started.json()["id"]
    wrong = client.post(f"/api/v1/practice/{session_id}/answers", json={"exercise_id": exercise_id, "answer": "Bye"})
    assert wrong.status_code == 200 and wrong.json()["correct"] is False
    finished = client.post("/api/v1/practice/finish", json={"session_id": session_id})
    assert finished.status_code == 200 and finished.json()["stars"] == 1
    with SessionLocal() as db:
        mistake = db.scalar(select(Mistake).where(Mistake.exercise_id == exercise_id))
        progress = db.scalar(select(LessonProgress).where(LessonProgress.lesson_id == lesson_id))
        assert mistake and mistake.srs_box == 1 and mistake.occurrence_count == 1
        assert progress and progress.completion_count == 1
    reviewed = client.post(f"/api/v1/learning/{student['id']}/review/mistakes/{mistake.id}", json={"correct": True})
    assert reviewed.status_code == 200 and reviewed.json()["box"] == 2


def test_tutor_rejects_forged_grade_context(client, student):
    lesson_id, _ = seed_lesson()
    session = client.post("/api/v1/sessions", json={"student_id": student["id"], "mode": "lesson"}).json()
    response = client.post("/api/v1/tutor/message", json={"session_id": session["id"], "text": "Hello", "learning_context": {"lesson_id": lesson_id, "book_id": "forged", "scenario": "同步巩固"}})
    assert response.status_code == 400
