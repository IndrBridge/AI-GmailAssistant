import pytest
from fastapi import status

def test_create_team(client, test_user, test_team):
    # First get the user id
    response = client.get(f"/api/users/email/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()["id"]
    
    response = client.post(
        "/api/teams/",
        json={**test_team, "created_by": user_id}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == test_team["name"]
    assert "id" in data

def test_get_user_teams(client, test_user):
    response = client.get(f"/api/teams/user/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_add_team_member(client, test_user, test_team):
    # First create a team
    team_response = client.post(
        "/api/teams/",
        json=test_team
    )
    team_id = team_response.json()["id"]
    
    # Then add a member
    response = client.post(
        f"/api/teams/{team_id}/members",
        json={
            "user_email": "member@example.com",
            "role": "member"
        }
    )
    assert response.status_code == status.HTTP_200_OK

def test_get_team_tasks(client, test_user, test_team):
    # First create a team
    team_response = client.post(
        "/api/teams/",
        json=test_team
    )
    team_id = team_response.json()["id"]
    
    response = client.get(f"/api/teams/{team_id}/tasks")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_update_team_not_found(client, test_team):
    response = client.put(
        "/api/teams/999",
        json={"name": "Updated Team"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_update_team_unauthorized(client, test_team):
    # First create a team
    team_response = client.post(
        "/api/teams/",
        json=test_team
    )
    team_id = team_response.json()["id"]
    
    # Try to update with different user
    response = client.put(
        f"/api/teams/{team_id}",
        json={"name": "Updated Team"},
        headers={"X-User-Email": "different@example.com"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN 