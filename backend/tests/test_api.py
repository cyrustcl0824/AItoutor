def test_auth_and_family_student_flow(client, parent):
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    created = client.post("/api/v1/students", json={"name": "Amy", "display_name": "Amy", "grade": 4, "preferences": {}})
    assert created.status_code == 201
    assert client.get("/api/v1/students").json()[0]["display_name"] == "Amy"
    assert "access_token" in client.cookies


def test_tutor_updates_learning_state(client, student):
    session = client.post("/api/v1/sessions", json={"student_id": student["id"], "mode": "conversation"})
    assert session.status_code == 201
    reply = client.post("/api/v1/tutor/message", json={"session_id": session.json()["id"], "text": "I have two cat."})
    assert reply.status_code == 200
    assert reply.json()["knowledge_point_code"] == "plural_nouns"
    mistakes = client.get(f"/api/v1/learning/{student['id']}/mistakes").json()
    progress = client.get(f"/api/v1/learning/{student['id']}/progress").json()
    assert len(mistakes) == 1
    assert progress[0]["score"] < 0.5


def test_disabled_subject_is_visible_but_not_enabled(client, parent):
    subjects = {item["code"]: item for item in client.get("/api/v1/subjects").json()}
    assert subjects["english"]["enabled"] is True
    assert subjects["math"]["enabled"] is False


def test_mock_audio_round_trip(client, parent):
    response = client.post("/api/v1/audio/speech", data={"text": "Hello!", "voice": "Emma"})
    assert response.status_code == 200
    audio = client.get(response.json()["url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/wav")

