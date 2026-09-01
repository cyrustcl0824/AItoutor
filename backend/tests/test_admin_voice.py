from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import get_settings
from app.database import SessionLocal
from app.models import Course, Exercise, Lesson, Story, Subject
from app.resource_sync import _safe_destination
from curriculum.import_textbooks import import_release_data
from sqlalchemy import func, select


@pytest.fixture
def runtime_ai_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RUNTIME_CONFIG_PATH", str(tmp_path / "config" / "ai.env"))
    monkeypatch.setenv("AUDIO_CACHE_ROOT", str(tmp_path / "audio"))
    monkeypatch.setenv("RESOURCE_ROOT", str(tmp_path / "resources"))
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def register(client, email: str):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a-secure-password", "family_name": "测试家庭"},
    )


def test_first_user_is_admin_and_parent_cannot_read_settings(client, runtime_ai_env):
    admin = register(client, "admin@example.com")
    assert admin.status_code == 201
    assert admin.json()["role"] == "admin"
    assert client.get("/api/v1/admin/settings/ai").status_code == 200

    parent = register(client, "parent-2@example.com")
    assert parent.status_code == 201
    assert parent.json()["role"] == "parent"
    assert client.get("/api/v1/admin/settings/ai").status_code == 403


def test_runtime_key_is_masked_and_never_returned(client, runtime_ai_env):
    register(client, "admin@example.com")
    payload = {
        "provider": "mock",
        "api_key": "dashscope-secret-1234",
        "clear_api_key": False,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "chat_model": "qwen-plus",
        "asr_model": "qwen3-asr-flash",
        "tts_model": "cosyvoice-v3-flash",
        "tts_voice": "longanyang",
        "tts_url": "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer",
    }
    response = client.put("/api/v1/admin/settings/ai", json=payload)
    assert response.status_code == 200
    assert response.json()["api_key_hint"] == "****1234"
    assert "dashscope-secret-1234" not in response.text
    assert "dashscope-secret-1234" in (runtime_ai_env / "config" / "ai.env").read_text(encoding="utf-8")
    assert client.post("/api/v1/admin/settings/ai/test").json()["chat"]["ok"] is True


def test_mock_voice_turn_returns_transcript_decision_and_audio(client, student, runtime_ai_env):
    session = client.post("/api/v1/sessions", json={"student_id": student["id"], "mode": "conversation"})
    response = client.post(
        "/api/v1/tutor/voice-turn",
        data={"session_id": session.json()["id"], "language": "en", "learning_context": '{"scenario":"同步巩固"}'},
        files={"audio": ("speech.wav", b"not-a-real-wave-but-valid-for-the-mock", "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "I like English."
    assert body["decision"]["reply"]
    assert client.get(body["audio"]["url"]).status_code == 200


def test_resource_job_can_be_created_and_canceled_without_downloading(client, runtime_ai_env, monkeypatch):
    register(client, "admin@example.com")
    monkeypatch.setattr("app.api.admin.start_worker", lambda _job_id: None)
    response = client.post(
        "/api/v1/admin/resources/sync",
        json={"packages": ["data"], "acknowledge_copyright": True},
    )
    assert response.status_code == 202
    job_id = response.json()["id"]
    canceled = client.post(f"/api/v1/admin/resources/jobs/{job_id}/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["cancel_requested"] is True


def test_resource_sync_requires_copyright_acknowledgement(client, runtime_ai_env):
    register(client, "admin@example.com")
    response = client.post(
        "/api/v1/admin/resources/sync",
        json={"packages": ["data"], "acknowledge_copyright": False},
    )
    assert response.status_code == 422


def test_archive_destination_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        _safe_destination(tmp_path, "../outside.txt")


def test_release_data_import_is_idempotent_and_preserves_grade(tmp_path):
    book = tmp_path / "books" / "english-g4up"
    (book / "lessons").mkdir(parents=True)
    (book / "outline.json").write_text(json.dumps({"textbook": "四年级上册", "units": [{"unit_number": 1, "title": "Hello", "knowledge_points": [{"name": "Greetings", "difficulty": 1}]}], "lessons": [{"id": "english-g4up-u1-kp1", "title": "Greetings", "unitNumber": 1, "kpIndex": 0}]}), encoding="utf-8")
    (book / "lessons" / "english-g4up-u1-kp1.json").write_text(json.dumps({"id": "english-g4up-u1-kp1", "unitNumber": 1, "questions": [{"id": 1, "knowledge_point": "Greetings", "question": "Say hello", "answer": "Hello", "type": "short_answer"}]}), encoding="utf-8")
    (book / "passages.json").write_text(json.dumps({"passages": []}), encoding="utf-8")
    (book / "stories.json").write_text(json.dumps({"stories": [{"id": "g4-story", "title": "Friends", "sentences": [{"text": "Hello!"}]}]}), encoding="utf-8")
    stats = lambda: {"courses_created": 0, "units_created": 0, "knowledge_points_created": 0, "exercises_created": 0, "exercises_updated": 0, "unmatched_quizzes": 0, "sentences_created": 0, "stories_created": 0, "story_sentences_created": 0, "damaged_passages": [], "damaged_stories": []}
    with SessionLocal() as db:
        subjects = {item.code: item for item in db.scalars(select(Subject))}
        import_release_data(db, tmp_path, subjects, stats()); db.commit()
        import_release_data(db, tmp_path, subjects, stats()); db.commit()
        assert db.scalar(select(func.count(Course.id))) == 1
        assert db.scalar(select(func.count(Lesson.id))) == 1
        assert db.scalar(select(func.count(Exercise.id))) == 1
        assert db.scalar(select(Story).where(Story.external_id == "g4-story")).grade == 4
