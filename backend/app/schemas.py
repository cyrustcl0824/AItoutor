from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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


class AISettingsUpdate(BaseModel):
    provider: Literal["mock", "dashscope"]
    api_key: str | None = Field(default=None, min_length=1, max_length=500)
    clear_api_key: bool = False
    base_url: str = Field(min_length=8, max_length=500)
    chat_model: str = Field(min_length=1, max_length=100)
    asr_model: str = Field(min_length=1, max_length=100)
    tts_model: str = Field(min_length=1, max_length=100)
    tts_voice: str = Field(min_length=1, max_length=100)
    tts_url: str = Field(min_length=8, max_length=500)

    @model_validator(mode="after")
    def validate_key_action(self):
        if self.api_key is not None:
            self.api_key = self.api_key.strip()
            if not self.api_key:
                raise ValueError("API Key cannot be blank")
        if self.api_key and self.clear_api_key:
            raise ValueError("API Key cannot be set and cleared at the same time")
        for field in ("base_url", "chat_model", "asr_model", "tts_model", "tts_voice", "tts_url"):
            value = getattr(self, field).strip()
            if not value:
                raise ValueError(f"{field} cannot be blank")
            setattr(self, field, value)
        return self


class ResourceSyncRequest(BaseModel):
    packages: list[Literal["data", "data_source", "textbook_pages", "story_images", "audio"]]
    acknowledge_copyright: bool


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
