# API Endpoint Tests

This document provides a comprehensive list of all API endpoints and how to test them using curl commands.

## Root Endpoint

### 1. Health Check
```bash
curl http://localhost:8000/
```

## Authentication Endpoints

### 2. Get OAuth URL
```bash
curl http://localhost:8000/api/oauth/url
```

### 3. OAuth Callback
```bash
curl "http://localhost:8000/api/oauth/callback?code=test_code"
```

### 4. Get Access Token
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=newtest@example.com&password=test_token_123"
```

### 5. Get Current User
```bash
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer ${TOKEN}"
```

## Task Management Endpoints

### 6. Options for Extract (CORS)
```bash
curl -X OPTIONS http://localhost:8000/api/extract
```

### 7. Extract Tasks from Email
```bash
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "content": "Please review the document by tomorrow",
    "gmail_id": "test_email_1",
    "user_email": "newtest@example.com",
    "thread_id": "thread_1",
    "subject": "Document Review",
    "sender": "manager@example.com",
    "received_at": "2024-12-26T11:30:00+05:30"
  }'
```

### 8. Get User Tasks
```bash
# Basic request
curl "http://localhost:8000/api/tasks/newtest@example.com" \
  -H "Authorization: Bearer ${TOKEN}"

# With filters
curl "http://localhost:8000/api/tasks/newtest@example.com?status=pending,in_progress&priority=high,medium&search_query=review" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 9. Update Task Status
```bash
curl -X PUT "http://localhost:8000/api/tasks/1/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "status": "in_progress",
    "title": "Updated title",
    "description": "Updated description",
    "priority": "high",
    "due_date": "2024-12-27T17:30:00+05:30",
    "reminder_time": "2024-12-26T17:30:00+05:30"
  }'
```

### 10. Confirm Task
```bash
curl -X POST "http://localhost:8000/api/tasks/1/confirm" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 11. Reject Task
```bash
curl -X POST "http://localhost:8000/api/tasks/1/reject" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 12. Create Test Tasks
```bash
curl -X POST "http://localhost:8000/api/tasks/test/newtest@example.com" \
  -H "Authorization: Bearer ${TOKEN}"
```

## Task Reminder Endpoints

### 13. Set Task Reminder
```bash
curl -X POST "http://localhost:8000/api/tasks/1/reminder" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "reminder_time": "2024-12-26T17:30:00+05:30"
  }'
```

### 14. Remove Task Reminder
```bash
curl -X DELETE "http://localhost:8000/api/tasks/1/reminder" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 15. Get Pending Reminders
```bash
curl "http://localhost:8000/api/tasks/reminders" \
  -H "Authorization: Bearer ${TOKEN}"
```

## Team Management Endpoints

### 16. Create Team
```bash
curl -X POST http://localhost:8000/api/teams \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "name": "Test Team",
    "description": "Test team description",
    "user_email": "newtest@example.com"
  }'
```

### 17. Get Teams
```bash
curl "http://localhost:8000/api/teams?user_email=newtest@example.com" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 18. Get Team Members
```bash
curl "http://localhost:8000/api/teams/1/members" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 19. Update Team
```bash
curl -X PUT "http://localhost:8000/api/teams/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "name": "Updated Test Team",
    "members": ["member1@example.com", "member2@example.com"]
  }'
```

### 20. Delete Team
```bash
curl -X DELETE "http://localhost:8000/api/teams/1" \
  -H "Authorization: Bearer ${TOKEN}"
```

## User Management Endpoints

### 21. Create User
```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newtest@example.com",
    "oauth_token": "test_token_123",
    "refresh_token": "refresh_token_123",
    "token_expiry": "2024-12-26T17:30:00+05:30"
  }'
```

## Email Processing Endpoints

### 22. Process Current Email
```bash
curl -X POST http://localhost:8000/api/emails/current/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "gmail_id": "test_email_process_1",
    "thread_id": "thread_1",
    "subject": "Q4 Report Review",
    "sender": "manager@example.com",
    "content": "Hi team,\n\nPlease review the Q4 report by tomorrow.\n\nThanks"
  }'
```

### 23. Generate Email Reply
```bash
curl -X POST http://localhost:8000/api/emails/current/reply \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "content": "Hi team,\n\nPlease review the Q4 report by tomorrow.\n\nThanks",
    "context": "This is a high-priority report that needs immediate attention."
  }'
```

## Application Events

### 24. Startup Event
```bash
# This is an internal FastAPI event that runs when the application starts
# No curl command needed as it's automatically triggered on startup
```

## Testing Notes

1. Replace `${TOKEN}` with a valid JWT token obtained from the `/token` endpoint
2. All timestamps should be in ISO format with timezone offset
3. The server must be running on `http://localhost:8000`
4. For testing with a new token, use these steps:
   ```bash
   # 1. Get a new token
   TOKEN=$(curl -X POST http://localhost:8000/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=password&username=newtest@example.com&password=test_token_123" \
     | jq -r .access_token)
   
   # 2. Use the token in subsequent requests
   curl http://localhost:8000/api/users/me \
     -H "Authorization: Bearer ${TOKEN}"
   ```
