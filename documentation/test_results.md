# API Endpoint Test Results 

This document contains the test results for all API endpoints using the curl commands specified in endpoint_tests.md.

## Root Endpoint 

### 1. Health Check 
```bash
curl http://localhost:8000/
```
**Status**: Success
**Response**: `{"message":"Hello from FastAPI MVP!"}`

## Authentication Endpoints 

### 2. Get OAuth URL 
```bash
curl http://localhost:8000/api/oauth/url
```
**Status**: Success
**Response**: Contains Google OAuth URL with correct scopes and parameters
**Note**: Visit this URL in a browser to start the real OAuth flow

### 3. OAuth Callback 
**Note**: This endpoint is now configured for real Google OAuth. To test:
1. Visit the OAuth URL in a browser
2. Complete Google's consent flow
3. The callback will automatically process the real OAuth code

The test with curl is no longer valid as we've removed test token support:
```bash
# This no longer works:
# curl "http://localhost:8000/api/oauth/callback?code=test_code"

# Instead, use real OAuth flow through browser
```

### 4. Get Access Token 
**Note**: This endpoint now requires real Google OAuth tokens. The previous test with hardcoded credentials will not work:
```bash
# This no longer works:
# curl -X POST http://localhost:8000/token -d "username=test@example.com&password=test_token_123"

# Instead, obtain tokens through the OAuth flow
```

### 5. Get Current User 
```bash
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJuZXd0ZXN0QGV4YW1wbGUuY29tIiwib2F1dGhfdG9rZW4iOiJ0ZXN0X3Rva2VuXzEyMyIsImV4cCI6MTczNTIxNjU3NH0.qP-fBYKuBKJHpr277t0AqmikkusbZp_AguF9k3Vv1n4"
```
**Status**: Success
**Response**: Returns user details including email, tasks, and emails

## Task Management Endpoints 

### 6. Options for Extract (CORS) 
```bash
curl -X OPTIONS http://localhost:8000/api/extract
```
**Status**: Success
**Response**: `{"message":"OK"}`

### 7. Extract Tasks from Email 
```bash
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "content": "Please review the document by tomorrow",
    "gmail_id": "test_email_extract_1",
    "user_email": "newtest@example.com",
    "thread_id": "thread_1",
    "subject": "Document Review",
    "sender": "manager@example.com",
    "received_at": "2024-12-26T11:30:00+05:30"
  }'
```
**Status**: Success
**Response**: Successfully extracted task with title "Review the document" and suggested reply

### 8. Get User Tasks 
```bash
curl http://localhost:8000/api/tasks/newtest@example.com \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Returns list of all tasks for the user with their details

### 9. Update Task Status 
```bash
curl -X PUT http://localhost:8000/api/tasks/61/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"status": "in_progress"}'
```
**Status**: Success
**Response**: Updated task status to "in_progress"

### 10. Confirm Task 
```bash
curl -X POST http://localhost:8000/api/tasks/61/confirm \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Task confirmed successfully

### 11. Reject Task "X"
```bash
curl -X POST http://localhost:8000/api/tasks/61/reject \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Task rejected successfully

### 12. Create Test Tasks 
```bash
curl -X POST "http://localhost:8000/api/tasks/test/newtest@example.com" \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Test tasks created successfully

### 13. Set Task Reminder 
```bash
curl -X POST http://localhost:8000/api/tasks/61/reminder \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"reminder_time": "2024-12-26T18:30:00+05:30"}'
```
**Status**: Success
**Response**: Reminder set successfully with updated task details

### 14. Remove Task Reminder 
```bash
curl -X DELETE http://localhost:8000/api/tasks/61/reminder \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Reminder removed successfully

### 15. Get Pending Reminders 
```bash
curl http://localhost:8000/api/tasks/reminders \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Failed
**Response**: Not authorized to access these tasks

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
**Status**: Success
**Response**: Team created successfully with ID 2

### 17. Get Teams 
```bash
curl http://localhost:8000/api/teams?user_email=newtest@example.com \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Returns list of teams with their details and members

### 18. Get Team Members 
```bash
curl http://localhost:8000/api/teams/2/members \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Returns list of team members with their roles

### 19. Update Team 
```bash
curl -X PUT http://localhost:8000/api/teams/2 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "name": "Updated Test Team",
    "members": ["member1@example.com", "member2@example.com"]
  }'
```
**Status**: Failed
**Response**: Invalid keyword argument error

### 20. Delete Team 
```bash
curl -X DELETE http://localhost:8000/api/teams/2 \
  -H "Authorization: Bearer ${TOKEN}"
```
**Status**: Success
**Response**: Team deleted successfully

## User Management Endpoints 

### 21. Create User 
```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "oauth_token": "test_token_123",
    "refresh_token": "refresh_token_123",
    "token_expiry": "2024-12-26T17:30:00+05:30"
  }'
```
**Status**: Success
**Response**: User created successfully

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
**Status**: Success
**Response**: Created task and generated suggested reply

### 23. Generate Email Reply 
```bash
curl -X POST http://localhost:8000/api/emails/current/reply \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "gmail_id": "test_email_reply_1",
    "content": "Hi team,\n\nPlease review the Q4 report by tomorrow.\n\nThanks",
    "context": "This is a high-priority report that needs immediate attention."
  }'
```
**Status**: Success
**Response**: Generated email reply with subject, tone analysis, and key points
