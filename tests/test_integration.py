
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL") or not os.getenv("REDIS_URL"):
        pytest.skip("Integration services not configured")
    return TestClient(app)


@pytest.fixture
def user():
    return f"test_{uuid.uuid4().hex[:12]}"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["postgres"] is True
    assert response.json()["redis"] is True


def test_decks(client, user):
    response = client.get("/decks", params={"user": user})
    assert response.status_code == 200

    data = response.json()
    assert data["user"] == user
    assert isinstance(data["decks"], list)
    assert len(data["decks"]) > 0


def test_due_cards(client, user):
    response = client.get(f"/study/{user}/due")
    assert response.status_code == 200

    data = response.json()
    assert data["user"] == user
    assert data["total_due"] >= 1
    assert data["day_starts_at"] == "04:00 +05:30"


def test_invalid_study_limit(client, user):
    response = client.post(
        f"/study/{user}/start",
        params={"limit": 0},
    )
    assert response.status_code == 400


def test_start_and_resume_queue(client, user):
    first = client.post(f"/study/{user}/start")
    assert first.status_code == 200
    assert first.json()["built"] is True

    second = client.post(f"/study/{user}/start")
    assert second.status_code == 200
    assert second.json()["built"] is False


def test_next_card(client, user):
    client.post(f"/study/{user}/start")

    response = client.get(f"/study/{user}/next")
    assert response.status_code == 200
    assert "front" in response.json()


def test_invalid_grade(client, user):
    response = client.post(
        f"/study/{user}/answer",
        json={"card_id": 1, "grade": 6},
    )
    assert response.status_code == 400


def test_answer_and_stats(client, user):
    start = client.post(f"/study/{user}/start")
    assert start.status_code == 200

    next_response = client.get(f"/study/{user}/next")
    assert next_response.status_code == 200
    card_id = next_response.json()["id"]

    answer = client.post(
        f"/study/{user}/answer",
        json={"card_id": card_id, "grade": 5},
    )
    assert answer.status_code == 200
    assert answer.json()["passed"] is True

    stats = client.get(f"/stats/{user}")
    assert stats.status_code == 200
    assert len(stats.json()["by_study_day"]) >= 1


def test_missing_card(client, user):
    response = client.post(
        f"/study/{user}/answer",
        json={"card_id": -999999, "grade": 4},
    )
    assert response.status_code == 404


def test_stats_without_answers(client, user):
    response = client.get(f"/stats/{user}")
    assert response.status_code == 404
