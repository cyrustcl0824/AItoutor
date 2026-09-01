from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    family_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: str
    email: str
    family_id: str
    role: str


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=80)
    grade: int = Field(ge=1, le=6)
    preferences: dict = Field(default_factory=dict)


class StudentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    grade: int | None = Field(default=None, ge=1, le=6)
    preferences: dict | None = None
    active: bool | None = None


class StudentOut(ORMModel):
    id: str
    name: str
    display_name: str
    grade: int
    preferences: dict
    active: bool


class SessionStart(BaseModel):
    student_id: str
    mode: Literal["conversation", "vocabulary", "lesson", "review", "speaking", "reading"] = "conversation"
    lesson_id: str | None = None


class LearningContextIn(BaseModel):
    book_id: str | None = None
    unit_id: str | None = None
    lesson_id: str | None = None
    scenario: Literal["课前预习", "课后作业", "同步巩固", "单元复习", "错题巩固", "期中期末复习"] = "同步巩固"
    available_minutes: int = Field(default=15, ge=1, le=120)


class TutorMessage(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=1000)
    learning_context: LearningContextIn | None = None


class PracticeStart(BaseModel):
    student_id: str
    lesson_id: str


class PracticeAnswer(BaseModel):
    exercise_id: str
    answer: str = Field(max_length=4000)


class PracticeFinish(BaseModel):
    session_id: str


class ReviewAnswer(BaseModel):
    correct: bool


class ReadingContentProgressIn(BaseModel):
    student_id: str
    sentence_position: int = Field(default=0, ge=0)
    page_id: str | None = None
    completed: bool = False


class TutorDecision(BaseModel):
    reply: str
    intent: str = "conversation"
    knowledge_point_code: str | None = None
    result: Literal["correct", "correct_after_hint", "partially_correct", "incorrect", "skipped"] | None = None
    hint_count: int = Field(default=0, ge=0, le=3)
    suggested_difficulty: int = Field(default=1, ge=1, le=5)
    should_end: bool = False


class ReadingProgressIn(BaseModel):
    student_id: str
    page_id: str | None = None
    sentence_position: int = Field(ge=0)
    completed: bool = False


class DeviceHeartbeat(BaseModel):
    device_id: str
    state: Literal["IDLE", "LISTENING", "UPLOADING", "THINKING", "SPEAKING"]
    metadata: dict = Field(default_factory=dict)
