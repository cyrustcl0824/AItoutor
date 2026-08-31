import os
import sys
from pathlib import Path

TEST_DB = Path(__file__).parent / "test.db"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AI_PROVIDER"] = "mock"
os.environ["SECRET_KEY"] = "test-secret-that-is-long-enough"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from app.main import startup
    startup()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def parent(client):
    response = client.post("/api/v1/auth/register", json={"email": "parent@example.com", "password": "a-secure-password", "family_name": "星星家庭"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def student(client, parent):
    response = client.post("/api/v1/students", json={"name": "小星", "display_name": "小星", "grade": 3, "preferences": {"interests": ["space"]}})
    assert response.status_code == 201
    return response.json()
