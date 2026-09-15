import asyncio
from copy import deepcopy

import httpx
import pytest

from src.app import activities, app


@pytest.fixture(autouse=True)
def restore_activity_state():
    original_activities = deepcopy(activities)

    yield

    activities.clear()
    activities.update(original_activities)


@pytest.fixture
def client():
    def request(method, url, **kwargs):
        async def send_request():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as async_client:
                return await async_client.request(method, url, **kwargs)

        return asyncio.run(send_request())

    return request


def test_get_activities_returns_activity_data(client):
    # Arrange
    expected_activity = activities["Chess Club"]

    # Act
    response = client("GET", "/activities")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert "Chess Club" in response_data
    assert response_data["Chess Club"]["participants"] == expected_activity["participants"]
    assert response_data["Chess Club"]["max_participants"] == expected_activity["max_participants"]


def test_signup_adds_participant_to_activity(client):
    # Arrange
    activity_name = "Soccer Club"
    email = "new.student@mergington.edu"

    # Act
    signup_response = client(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )
    activities_response = client("GET", "/activities")

    # Assert
    assert signup_response.status_code == 200
    assert signup_response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    assert email in activities_response.json()[activity_name]["participants"]


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "new.student@mergington.edu"

    # Act
    response = client(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = activities[activity_name]["participants"][0]

    # Act
    response = client(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }


def test_delete_removes_participant_from_activity(client):
    # Arrange
    activity_name = "Chess Club"
    email = activities[activity_name]["participants"][0]

    # Act
    delete_response = client(
        "DELETE",
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )
    activities_response = client("GET", "/activities")

    # Assert
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "message": f"Removed {email} from {activity_name}"
    }
    assert email not in activities_response.json()[activity_name]["participants"]


def test_delete_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client(
        "DELETE",
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_delete_rejects_missing_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "missing.student@mergington.edu"

    # Act
    response = client(
        "DELETE",
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Participant not found"}