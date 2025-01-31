import pytest
from fastapi import status
from datetime import datetime, timedelta

def test_create_task(client, test_user, test_task):
    # First get the user id
    response = client.get(f"/api/users/email/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()["id"]
    
    # Add user_id to task data
    task_data = {**test_task, "user_id": user_id}
    
    response = client.post(
        "/api/tasks/",
        json=task_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == test_task["title"]
    assert "id" in data

def test_update_task(client, test_user, test_task):
    # First get the user id
    response = client.get(f"/api/users/email/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()["id"]
    
    # Add user_id to task data
    task_data = {**test_task, "user_id": user_id}
    
    # First create a task
    task_response = client.post(
        "/api/tasks/",
        json=task_data
    )
    task_id = task_response.json()["id"]
    
    # Then update it
    update_data = {
        "status": "in_progress",
        "priority": "high"
    }
    response = client.put(
        f"/api/tasks/{task_id}",
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == update_data["status"]
    assert data["priority"] == update_data["priority"]

def test_get_user_tasks(client, test_user):
    response = client.get(f"/api/tasks/user/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_get_task_history(client, test_user, test_task):
    # First get the user id
    response = client.get(f"/api/users/email/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()["id"]
    
    # Add user_id to task data
    task_data = {**test_task, "user_id": user_id}
    
    # First create a task
    task_response = client.post(
        "/api/tasks/",
        json=task_data
    )
    task_id = task_response.json()["id"]
    
    # Then get its history
    response = client.get(f"/api/tasks/{task_id}/history")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_complete_task(client, test_user, test_task):
    # First get the user id
    response = client.get(f"/api/users/email/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()["id"]
    
    # Add user_id to task data
    task_data = {**test_task, "user_id": user_id}
    
    # First create a task
    task_response = client.post(
        "/api/tasks/",
        json=task_data
    )
    task_id = task_response.json()["id"]
    
    # Then complete it
    response = client.post(f"/api/tasks/{task_id}/complete")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Task marked as completed"

def test_get_task_analytics(client, test_user):
    response = client.get(
        "/api/tasks/analytics",
        params={"user_id": test_user["email"]}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "task_metrics" in data
    assert "distributions" in data

def test_get_upcoming_tasks(client, test_user):
    response = client.get(
        "/api/tasks/upcoming",
        params={"user_id": test_user["email"]}
    )
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_get_overdue_tasks(client, test_user):
    response = client.get(
        "/api/tasks/overdue",
        params={"user_id": test_user["email"]}
    )
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_set_task_reminder(client, test_user, test_task):
    # First get the user id
    response = client.get(f"/api/users/email/{test_user['email']}")
    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()["id"]
    
    # Add user_id to task data
    task_data = {**test_task, "user_id": user_id}
    
    # First create a task
    task_response = client.post(
        "/api/tasks/",
        json=task_data
    )
    task_id = task_response.json()["id"]
    
    # Set reminder
    reminder_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    response = client.post(
        f"/api/tasks/{task_id}/reminder",
        json={"reminder_time": reminder_time}
    )
    assert response.status_code == status.HTTP_200_OK

def test_get_task_reminders(client, test_user):
    response = client.get("/api/tasks/reminders")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list) 