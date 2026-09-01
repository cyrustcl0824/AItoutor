from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uid() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Family(Base, TimestampMixin):
    __tablename__ = "families"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    family_id: Mapped[str] = mapped_column(ForeignKey("families.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="parent")
    refresh_version: Mapped[int] = mapped_column(Integer, default=0)


class Student(Base, TimestampMixin):
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    family_id: Mapped[str] = mapped_column(ForeignKey("families.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    display_name: Mapped[str] = mapped_column(String(80))
    grade: Mapped[int] = mapped_column(Integer)
    age_group: Mapped[str] = mapped_column(String(20), default="6-12")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(150), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    grade: Mapped[int] = mapped_column(Integer)
    semester: Mapped[str] = mapped_column(String(30))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class Unit(Base):
    __tablename__ = "units"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(150), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)


class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(150), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class Exercise(Base):
    __tablename__ = "exercises"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    lesson_id: Mapped[str | None] = mapped_column(ForeignKey("lessons.id"), nullable=True)
    knowledge_point_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(150), unique=True)
    prompt: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30), default="short_answer")
    options: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(200), default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class LearningSession(Base, TimestampMixin):
    __tablename__ = "learning_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    lesson_id: Mapped[str | None] = mapped_column(ForeignKey("lessons.id"), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")


class ConversationSession(Base, TimestampMixin):
    __tablename__ = "conversation_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    learning_session_id: Mapped[str] = mapped_column(ForeignKey("learning_sessions.id"), unique=True)
    topic: Mapped[str] = mapped_column(String(100), default="free conversation")
    level: Mapped[int] = mapped_column(Integer, default=1)


class Utterance(Base):
    __tablename__ = "utterances"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    conversation_session_id: Mapped[str] = mapped_column(ForeignKey("conversation_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    asr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_asset_id: Mapped[str | None] = mapped_column(ForeignKey("audio_assets.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    exercise_id: Mapped[str | None] = mapped_column(ForeignKey("exercises.id"), nullable=True)
    knowledge_point_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True)
    answer: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(String(30))
    hint_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Mistake(Base):
    __tablename__ = "mistakes"
    __table_args__ = (UniqueConstraint("student_id", "knowledge_point_id", "content", name="uq_mistake"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    exercise_id: Mapped[str | None] = mapped_column(ForeignKey("exercises.id"), nullable=True, index=True)
    knowledge_point_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    mistake_type: Mapped[str] = mapped_column(String(80), default="general")
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    srs_box: Mapped[int] = mapped_column(Integer, default=1)
    review_correct_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    graduated: Mapped[bool] = mapped_column(Boolean, default=False)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("student_id", "lesson_id", name="uq_lesson_progress"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)
    best_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    completion_count: Mapped[int] = mapped_column(Integer, default=0)
    first_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Mastery(Base):
    __tablename__ = "masteries"
    __table_args__ = (UniqueConstraint("student_id", "knowledge_point_id", name="uq_mastery"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    knowledge_point_id: Mapped[str] = mapped_column(ForeignKey("knowledge_points.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.1)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_streak: Mapped[int] = mapped_column(Integer, default=0)
    difficult_streak: Mapped[int] = mapped_column(Integer, default=0)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    knowledge_point_id: Mapped[str] = mapped_column(ForeignKey("knowledge_points.id"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    word: Mapped[str] = mapped_column(String(100))
    definition: Mapped[str] = mapped_column(Text, default="")
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)


class AudioAsset(Base):
    __tablename__ = "audio_assets"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(30))
    voice: Mapped[str] = mapped_column(String(80))
    mime_type: Mapped[str] = mapped_column(String(80))
    file_path: Mapped[str] = mapped_column(String(500))
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TextbookEdition(Base):
    __tablename__ = "textbook_editions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(150), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(100), default="")
    grade: Mapped[int] = mapped_column(Integer)
    semester: Mapped[str] = mapped_column(String(30))
    source_commit: Mapped[str] = mapped_column(String(80), default="")


class TextbookPage(Base):
    __tablename__ = "textbook_pages"
    __table_args__ = (UniqueConstraint("edition_id", "position", name="uq_edition_page"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    edition_id: Mapped[str] = mapped_column(ForeignKey("textbook_editions.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    printed_page: Mapped[str | None] = mapped_column(String(20), nullable=True)
    original_path: Mapped[str] = mapped_column(String(500))
    web_path: Mapped[str] = mapped_column(String(500))
    thumbnail_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)


class LessonPageLink(Base):
    __tablename__ = "lesson_page_links"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)
    start_page_id: Mapped[str] = mapped_column(ForeignKey("textbook_pages.id"))
    end_page_id: Mapped[str] = mapped_column(ForeignKey("textbook_pages.id"))


class Passage(Base):
    __tablename__ = "passages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(150), unique=True)
    title: Mapped[str] = mapped_column(String(200))


class PassageSentence(Base):
    __tablename__ = "passage_sentences"
    __table_args__ = (UniqueConstraint("passage_id", "position", name="uq_passage_sentence"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    passage_id: Mapped[str] = mapped_column(ForeignKey("passages.id"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("textbook_pages.id"), nullable=True)
    audio_asset_id: Mapped[str | None] = mapped_column(ForeignKey("audio_assets.id"), nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Story(Base):
    __tablename__ = "stories"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(150), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    grade: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer, default=1)
    cover_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(200), default="")


class StorySentence(Base):
    __tablename__ = "story_sentences"
    __table_args__ = (UniqueConstraint("story_id", "position", name="uq_story_sentence"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), index=True)
    audio_asset_id: Mapped[str | None] = mapped_column(ForeignKey("audio_assets.id"), nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    translation: Mapped[str] = mapped_column(Text, default="")
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    __table_args__ = (UniqueConstraint("student_id", "content_kind", "content_id", name="uq_reading_content_progress"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    passage_id: Mapped[str | None] = mapped_column(ForeignKey("passages.id"), nullable=True, index=True)
    content_kind: Mapped[str] = mapped_column(String(20), default="passage")
    content_id: Mapped[str] = mapped_column(String, index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("textbook_pages.id"), nullable=True)
    sentence_position: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    family_id: Mapped[str] = mapped_column(ForeignKey("families.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    device_type: Mapped[str] = mapped_column(String(30), default="m5stack")
    state: Mapped[str] = mapped_column(String(30), default="IDLE")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class ResourceSyncJob(Base, TimestampMixin):
    __tablename__ = "resource_sync_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(30), default="queued")
    current_package: Mapped[str | None] = mapped_column(String(80), nullable=True)
    downloaded_bytes: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int] = mapped_column(Integer, default=0)
    packages_json: Mapped[list] = mapped_column("packages", JSON, default=list)
    result_json: Mapped[dict] = mapped_column("result", JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    changed_fields: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
