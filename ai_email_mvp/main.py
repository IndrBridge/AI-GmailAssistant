import os
from dotenv import load_dotenv
import openai
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from datetime import datetime, timedelta
import time
from pytz import UTC
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

from app.database import SessionLocal, engine, get_db
from app import models, schemas, crud, auth, oauth
from app.background_tasks import reminder_background_task
import asyncio

# Initialize FastAPI app
app = FastAPI()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",  # Allow all Chrome extensions
        "http://localhost:8000",
        "https://mail.google.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in .env file")

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# OAuth endpoints
@app.get("/api/oauth/url")
async def get_oauth_url():
    """Get the Google OAuth URL."""
    try:
        # Use localhost:8000 for development
        redirect_uri = "http://localhost:8000/api/oauth/callback"
        auth_url = oauth.get_oauth_url(redirect_uri)
        return {"url": auth_url}
    except Exception as e:
        logger.error(f"Error getting OAuth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating OAuth URL"
        )

@app.get("/api/oauth/callback")
async def oauth_callback(
    code: str,
    db: Session = Depends(get_db)
):
    """Handle the OAuth callback."""
    try:
        result = await oauth.handle_oauth_callback(code, db)
        return result
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing OAuth callback"
        )

@app.post("/api/oauth/callback")
async def oauth_callback(
    token_data: dict,
    db: Session = Depends(get_db)
):
    """Handle the OAuth token from Chrome extension."""
    try:
        logger.info("=== Starting OAuth callback ===")
        logger.info(f"Received token data keys: {list(token_data.keys())}")
        
        token = token_data.get('token')
        if not token:
            logger.error("Token not provided in request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token not provided"
            )

        logger.info("Creating credentials from Chrome identity token")
        credentials = Credentials(
            token=token,
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            token_uri="https://oauth2.googleapis.com/token",
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.labels',
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
        )
        
        logger.info("Getting user info from Google")
        user_info = await oauth.get_user_info(credentials)
        if not user_info or 'email' not in user_info:
            logger.error(f"Failed to get user info from Google: {user_info}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        logger.info(f"Got user info for: {user_info['email']}")
        
        # Create or update user
        user = crud.get_user_by_email(db, user_info['email'])
        if not user:
            logger.info("Creating new user")
            user_create = schemas.UserCreate(
                email=user_info['email'],
                oauth_token=token
            )
            user = crud.create_user(db, user_create)
        else:
            logger.info("Updating existing user")
            user.oauth_token = token
            db.commit()
        
        # Create access token for our API
        logger.info("Creating access token")
        access_token = auth.create_access_token(
            data={
                "sub": user_info['email'],
                "oauth_token": token
            },
            expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        response_data = {
            "access_token": access_token,
            "token_type": "bearer"
        }
        logger.info("=== OAuth callback completed successfully ===")
        return response_data
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing OAuth callback: {str(e)}"
        )

# Authentication endpoints
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Get an access token using OAuth credentials."""
    try:
        # Verify user exists
        user = crud.get_user_by_email(db, form_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token = auth.create_google_token(user.email, user.oauth_token)
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        logger.error(f"Error in login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating access token"
        )

@app.get("/api/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user information."""
    try:
        logger.info("=== Getting current user info ===")
        if not current_user:
            logger.error("No current user found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.info(f"Returning user info for: {current_user.email}")
        return current_user
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/")
async def read_root():
    return {"message": "Hello from FastAPI MVP!"}

@app.options("/api/extract")
async def options_extract():
    return {"message": "OK"}

@app.post("/api/extract")
async def api_extract_tasks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)  # Add authentication
):
    """Extract tasks from email content."""
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ["content", "gmail_id", "user_email"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Verify user has access
        if current_user.email != data["user_email"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create tasks for this user"
            )
        
        # Create or update email
        email_data = schemas.EmailCreate(
            gmail_id=data["gmail_id"],
            content=data["content"],
            received_at=data.get("received_at"),
            subject=data.get("subject"),
            sender=data.get("sender")
        )
        
        email = crud.create_email(db, email_data, current_user.id)
        
        # Extract tasks
        result = extract_tasks_from_email(email.content)
        tasks = result.get("tasks", [])
        suggested_reply = result.get("suggested_reply")
        
        # Create tasks
        created_tasks = []
        for task in tasks:
            task_data = schemas.TaskCreate(
                title=task["title"],
                description=task.get("description", task["title"]),  # Use description if available, else title
                priority=task.get("priority", "medium"),
                due_date=task.get("due_date"),
                email_id=email.id,  # Pass email.id
                user_id=current_user.id
            )
            created_task = crud.create_task(db, task_data, current_user.id)  # Pass user_id
            created_tasks.append(created_task)
        
        return {
            "message": f"Successfully extracted {len(created_tasks)} tasks",
            "tasks": created_tasks,
            "suggested_reply": suggested_reply
        }
        
    except Exception as e:
        logger.error(f"Error extracting tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/tasks/{user_email}")
async def get_user_tasks(
    user_email: str,
    filter_params: schemas.TaskFilter = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get tasks for a user with optional filtering."""
    try:
        # Verify user has access
        if current_user.email != user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access these tasks"
            )
        
        tasks = crud.get_user_tasks(db, user_email, filter_params)
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.put("/api/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db)
):
    try:
        updated_task = crud.update_task(db, task_id, task_update)
        if not updated_task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return {
            "id": updated_task.id,
            "title": updated_task.title,
            "description": updated_task.description,
            "priority": updated_task.priority,
            "status": updated_task.status,
            "due_date": updated_task.due_date,
            "reminder_time": updated_task.reminder_time,
            "completed_at": updated_task.completed_at,
            "updated_at": updated_task.updated_at
        }
    except Exception as e:
        logger.error(f"Error in /api/tasks/{task_id}/status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/confirm")
async def confirm_task(task_id: int, db: Session = Depends(get_db)):
    try:
        task_update = schemas.TaskUpdate(status=schemas.TaskStatus.completed)
        updated_task = crud.update_task(db, task_id, task_update)
        if not updated_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"message": "Task confirmed successfully"}
    except Exception as e:
        logger.error(f"Error confirming task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/reject")
async def reject_task(task_id: int, db: Session = Depends(get_db)):
    try:
        task_update = schemas.TaskUpdate(status=schemas.TaskStatus.deleted)
        updated_task = crud.update_task(db, task_id, task_update)
        if not updated_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"message": "Task rejected successfully"}
    except Exception as e:
        logger.error(f"Error rejecting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Team Management Endpoints
@app.post("/api/teams")
async def create_team(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        logger.info(f"Creating team with data: {data}")
        
        # Validate required fields
        if not data.get('name'):
            raise HTTPException(status_code=400, detail="Team name is required")
        if not data.get('user_email'):
            raise HTTPException(status_code=400, detail="User email is required")
        
        # Get user from email
        user = crud.get_user_by_email(db, data['user_email'])
        logger.info(f"Found user: {user}")
        if not user:
            logger.error(f"User not found for email: {data['user_email']}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create team
        team = models.Team(
            name=data['name'],
            description=data.get('description', ''),
            created_by=user.id
        )
        logger.info(f"Creating team: {team.__dict__}")
        db.add(team)
        db.flush()  # Get team ID
        
        # Add creator as admin
        admin_member = models.TeamMember(
            team_id=team.id,
            user_id=user.id,
            role='admin'
        )
        logger.info(f"Adding admin member: {admin_member.__dict__}")
        db.add(admin_member)
        
        # Add other members
        for member_email in data.get('members', []):
            logger.info(f"Processing member: {member_email}")
            # Get or create member user
            member_user = crud.get_user_by_email(db, member_email)
            if not member_user:
                logger.info(f"Creating new user for member: {member_email}")
                member_user = models.User(
                    email=member_email,
                    oauth_token="",
                    refresh_token=None,
                    token_expiry=None
                )
                db.add(member_user)
                db.flush()
            
            team_member = models.TeamMember(
                team_id=team.id,
                user_id=member_user.id,
                role='member'
            )
            logger.info(f"Adding team member: {team_member.__dict__}")
            db.add(team_member)
        
        db.commit()
        logger.info("Team created successfully")
        
        return {"message": "Team created successfully", "team_id": team.id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating team: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/teams")
async def get_teams(request: Request, db: Session = Depends(get_db)):
    try:
        # Get user email from query params or headers
        user_email = request.query_params.get('user_email')
        if not user_email:
            raise HTTPException(status_code=400, detail="User email is required")
        
        # Get user's teams
        user = crud.get_user_by_email(db, user_email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get teams where user is a member
        teams = db.query(models.Team).join(
            models.TeamMember,
            models.Team.id == models.TeamMember.team_id
        ).filter(
            models.TeamMember.user_id == user.id
        ).all()
        
        return [{
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "created_at": team.created_at,
            "members": [member.user.email for member in team.members]
        } for team in teams]
    
    except Exception as e:
        logger.error(f"Error getting teams: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/teams/{team_id}/members")
async def get_team_members(team_id: int, db: Session = Depends(get_db)):
    try:
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        members = []
        for member in team.members:
            user = member.user
            members.append({
                "id": user.id,
                "email": user.email,
                "role": member.role,
                "joined_at": member.joined_at
            })
        
        return members
    
    except Exception as e:
        logger.error(f"Error getting team members: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/teams/{team_id}")
async def update_team(team_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        logger.info(f"Updating team {team_id} with data: {data}")
        
        # Get team
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Update team name
        if 'name' in data:
            team.name = data['name']
        
        # Update members if provided
        if 'members' in data:
            # Remove existing members except admin
            db.query(models.TeamMember).filter(
                models.TeamMember.team_id == team_id,
                models.TeamMember.role != 'admin'
            ).delete()
            
            # Get admin member
            admin_member = db.query(models.TeamMember).filter(
                models.TeamMember.team_id == team_id,
                models.TeamMember.role == 'admin'
            ).first()
            
            # Add new members
            for member_email in data['members']:
                # Skip if this is the admin's email
                if admin_member and member_email == admin_member.user.email:
                    continue
                    
                # Get or create member user
                member_user = crud.get_user_by_email(db, member_email)
                if not member_user:
                    member_user = models.User(
                        email=member_email,
                        oauth_token="",
                        refresh_token=None,
                        token_expiry=None
                    )
                    db.add(member_user)
                    db.flush()
                
                # Add as team member
                team_member = models.TeamMember(
                    team_id=team_id,
                    user_id=member_user.id,
                    role='member'
                )
                db.add(team_member)
        
        # Commit changes
        db.commit()
        
        # Return updated team data
        return {
            "message": "Team updated successfully",
            "team": {
                "id": team.id,
                "name": team.name,
                "members": [member.user.email for member in team.members]
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating team: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/teams/{team_id}")
async def delete_team(team_id: int, db: Session = Depends(get_db)):
    try:
        # Get team
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Delete team members first
        db.query(models.TeamMember).filter(models.TeamMember.team_id == team_id).delete()
        
        # Delete team
        db.query(models.Team).filter(models.Team.id == team_id).delete()
        
        # Commit changes
        db.commit()
        
        return {"message": "Team deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting team: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users")
async def create_user(request: Request, db: Session = Depends(get_db)):
    """Create a new user."""
    try:
        data = await request.json()
        logger.info(f"Creating user: {data}")
        
        # Validate required fields
        if 'email' not in data:
            raise HTTPException(status_code=400, detail="Email is required")
        if 'oauth_token' not in data:
            raise HTTPException(status_code=400, detail="OAuth token is required")
            
        # Create user schema for validation
        try:
            user_data = schemas.UserCreate(
                email=data['email'],
                oauth_token=data['oauth_token'],
                refresh_token=data.get('refresh_token'),
                token_expiry=data.get('token_expiry')
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        # Check for existing user
        existing_user = crud.get_user_by_email(db, data['email'])
        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="User with this email already exists"
            )
            
        # Create new user
        user = crud.create_user(db, user_data)
        return {
            "status": "success",
            "user": {
                "email": user.email,
                "oauth_token": user.oauth_token
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/test/{user_email}")
async def create_test_tasks(
    user_email: str,
    db: Session = Depends(get_db)
):
    try:
        tasks = crud.create_test_task(db, user_email)
        return {"message": "Test tasks created successfully"}
    except Exception as e:
        logger.error(f"Error creating test tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Task Reminder Endpoints
@app.post("/api/tasks/{task_id}/reminder")
async def set_task_reminder(
    task_id: int,
    reminder: schemas.ReminderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Set or update a reminder for a task."""
    try:
        # Get the task
        task = crud.get_task(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Verify task ownership
        if task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this task")
            
        # Update task with reminder (reminder_time is already validated and converted to UTC in the schema)
        task_update = schemas.TaskUpdate(reminder_time=reminder.reminder_time)
        updated_task = crud.update_task(db, task_id, task_update)
        
        return {"message": "Reminder set successfully", "task": updated_task}
        
    except Exception as e:
        logger.error(f"Error setting reminder for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/api/tasks/{task_id}/reminder")
async def remove_task_reminder(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Remove a reminder from a task."""
    try:
        # Get the task
        task = crud.get_task(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Verify task ownership
        if task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this task")
            
        # Remove reminder
        task_update = schemas.TaskUpdate(reminder_time=None)
        updated_task = crud.update_task(db, task_id, task_update)
        
        return {"message": "Reminder removed successfully", "task": updated_task}
        
    except Exception as e:
        logger.error(f"Error removing reminder for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/tasks/reminders")
async def get_pending_reminders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all pending reminders for the current user."""
    try:
        logger.info(f"Getting reminders for user {current_user.id}")
        
        # Verify user exists and is active
        if not current_user:
            logger.error("User not found or inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
            
        # Get tasks with pending reminders
        try:
            tasks = crud.get_tasks_with_reminders(db, current_user.id)
            logger.info(f"Found {len(tasks)} reminders for user {current_user.id}")
        except Exception as e:
            logger.error(f"Database error getting reminders: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
            
        # Return empty list if no reminders found
        if not tasks:
            return {"reminders": []}
            
        return {
            "reminders": [
                {
                    "task_id": task.id,
                    "title": task.title,
                    "reminder_time": task.reminder_time,
                    "status": task.status,
                    "priority": task.priority
                } for task in tasks
            ]
        }
        
    except HTTPException as e:
        logger.error(f"HTTP error getting reminders: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error getting reminders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

# Current Email Processing Endpoints
@app.options("/api/emails/current/process")
async def options_process_email():
    return {"message": "OK"}

@app.post("/api/emails/current/process", response_model=schemas.EmailProcessResponse)
async def process_current_email(
    email_data: schemas.CurrentEmailProcess,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Process the current email and return tasks and suggestions."""
    try:
        # Create email in database
        email_create = schemas.EmailCreate(
            gmail_id=email_data.gmail_id,
            thread_id=email_data.thread_id,
            subject=email_data.subject,
            sender=email_data.sender,
            content=email_data.content,
            received_at=datetime.now(timezone.utc)
        )
        email = crud.create_email(db=db, email=email_create, user_id=current_user.id)
        
        # Extract tasks using existing functionality
        ai_result = extract_tasks_from_email(email_data.content)
        tasks = ai_result.get("tasks", [])
        suggested_reply = ai_result.get("suggested_reply")

        # Create tasks
        created_tasks = []
        for task in tasks:
            task_data = schemas.TaskCreate(
                title=task["title"],
                description=task.get("description"),
                priority=task.get("priority", "medium"),
                due_date=task.get("due_date"),
                email_id=email.id,
                user_id=current_user.id
            )
            created_task = crud.create_task(db=db, task=task_data, user_id=current_user.id)
            created_tasks.append(created_task)

        # Generate a summary using OpenAI
        summary_prompt = f"Summarize this email in 2-3 sentences:\n\n{email_data.content}"
        client = openai.OpenAI()
        summary_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes emails concisely."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        summary = summary_response.choices[0].message.content.strip()

        return {
            "tasks": created_tasks,
            "suggested_reply": suggested_reply,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")

@app.post("/api/emails/current/reply", response_model=schemas.EmailReplyResponse)
async def generate_email_reply(
    reply_data: schemas.CurrentEmailReply,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Generate AI reply for current email."""
    try:
        # Construct the prompt for reply generation
        context = reply_data.context if reply_data.context else ""
        prompt = f"""
        Generate a professional email reply. Here's the context:
        
        Original Email:
        {reply_data.content}
        
        Additional Context (if any):
        {context}
        
        Generate a reply that is:
        1. Professional and courteous
        2. Addresses key points from the original email
        3. Clear and concise
        4. Maintains appropriate tone
        
        Also identify:
        1. The tone of your reply
        2. Key points being addressed
        """

        # Get response from OpenAI
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional email assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response to extract reply, tone, and key points
        full_response = response.choices[0].message.content.strip()
        
        # Split the response into sections (assuming AI formats it properly)
        sections = full_response.split("\n\n")
        suggested_reply = sections[0].strip()
        
        # Extract tone and key points from the remaining sections
        tone = "professional"  # default
        key_points = []
        
        for section in sections[1:]:
            if "tone:" in section.lower():
                tone = section.split(":", 1)[1].strip()
            elif "key points:" in section.lower():
                points = section.split(":", 1)[1].strip()
                key_points = [point.strip("- ") for point in points.split("\n") if point.strip()]

        return {
            "suggested_reply": suggested_reply,
            "tone": tone,
            "key_points_addressed": key_points
        }

    except Exception as e:
        logger.error(f"Error generating email reply: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating email reply: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the application starts."""
    asyncio.create_task(reminder_background_task())
    logger.info("Started reminder background task")

def parse_due_date(due_date_str: str) -> Optional[datetime]:
    """Parse a date string into a datetime object.
    
    Handles:
    - ISO format dates (YYYY-MM-DD)
    - Relative dates (today, tomorrow, next Friday)
    - Natural language dates (next week, in 2 days)
    
    Returns None if the date cannot be parsed.
    """
    try:
        if not due_date_str:
            return None
            
        due_date_str = due_date_str.lower().strip()
        
        # Handle special keywords
        if due_date_str == "today":
            return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        elif due_date_str == "tomorrow":
            return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif due_date_str == "asap":
            return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        # Try parsing ISO format first
        try:
            return datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            pass
            
        # Handle "next" relative dates
        days_mapping = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        if due_date_str.startswith("next "):
            day_name = due_date_str.split("next ")[1].strip().lower()
            if day_name in days_mapping:
                today = datetime.now(timezone.utc)
                current_day = today.weekday()
                target_day = days_mapping[day_name]
                
                # Calculate days until next occurrence
                days_until = target_day - current_day
                if days_until <= 0:  # If target day has passed this week
                    days_until += 7
                    
                return (today + timedelta(days=days_until)).replace(hour=0, minute=0, second=0, microsecond=0)
                
        # Handle "in X days/weeks"
        if due_date_str.startswith("in "):
            parts = due_date_str.split()
            if len(parts) >= 3 and parts[1].isdigit():
                number = int(parts[1])
                unit = parts[2].lower()
                
                if unit.startswith("day"):
                    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=number)
                elif unit.startswith("week"):
                    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(weeks=number)
                    
        return None
        
    except Exception as e:
        logger.error(f"Error parsing date '{due_date_str}': {e}")
        return None

def extract_tasks_from_email(content: str) -> dict:
    try:
        logger.info("Starting task extraction")
        logger.info(f"Email content length: {len(content)} characters")
        
        # Clean HTML content first
        if "<html" in content.lower() or "<body" in content.lower():
            from bs4 import BeautifulSoup
            import re
            
            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            content = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in content.splitlines())
            content = ' '.join(chunk for chunk in lines if chunk)
            
            logger.info(f"Cleaned HTML content length: {len(content)} characters")
        
        # Truncate content if too long (GPT-4 has ~8k token limit, roughly 32k chars)
        MAX_CONTENT_LENGTH = 24000  # Leave room for prompts and other context
        if len(content) > MAX_CONTENT_LENGTH:
            logger.info(f"Content too long ({len(content)} chars). Truncating to {MAX_CONTENT_LENGTH} chars")
            # Try to truncate at a sentence or paragraph boundary
            truncation_point = content[:MAX_CONTENT_LENGTH].rfind('.')
            if truncation_point == -1:
                truncation_point = content[:MAX_CONTENT_LENGTH].rfind('\n')
            if truncation_point == -1:
                truncation_point = MAX_CONTENT_LENGTH
            content = content[:truncation_point] + "\n[Email truncated due to length...]"
        
        # Create a more structured prompt
        system_prompt = """You are an AI assistant that extracts actionable tasks from emails, specializing in educational and professional development contexts.
Focus on identifying:
1. Application deadlines and important dates
2. Required documentation or materials to prepare
3. Information session or meeting attendance requirements
4. Registration or submission deadlines
5. Follow-up actions needed
6. Scholarship or financial aid deadlines
7. Academic requirements or prerequisites

For each task:
- Be specific about deadlines using YYYY-MM-DD format (e.g., 2024-12-29)
- For relative dates, use: "today", "tomorrow", "asap"
- For tasks without a specific deadline, use null
- Include any preparation requirements
- Note if there are financial implications
- Highlight priority based on deadlines"""

        user_prompt = f"""Please analyze this email and extract:
1. All actionable tasks and deadlines
2. A suggested reply (if appropriate)

For each identified task, consider:
- Is there a specific deadline? Convert all dates to YYYY-MM-DD format
- Are there any prerequisites?
- Is there any financial aspect?
- What preparation is needed?

Email content:
{content}

Return your analysis in this exact JSON format:
{{
    "tasks": [
        {{
            "title": "Clear, actionable task description",
            "due_date": "YYYY-MM-DD or null if no specific date",
            "priority": "high/medium/low",
            "preparation": "What needs to be prepared",
            "financial_aspects": "Any financial implications"
        }}
    ],
    "suggested_reply": "A polite and professional reply if needed, or null"
}}"""

        logger.info("Making OpenAI API call")
        # Make API call with proper error handling and retry logic
        max_retries = 3
        retry_count = 0
        retry_delay = 1  # Initial delay in seconds
        
        while retry_count < max_retries:
            try:
                # Check if API key is valid
                if not openai.api_key:
                    raise ValueError("OpenAI API key is not configured")

                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-4",  # Using GPT-4 for better task extraction
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2  # Lower temperature for more consistent output
                )
                
                # Extract and validate response
                result = response.choices[0].message.content.strip()
                logger.info(f"Raw OpenAI Response: {result}")
                
                try:
                    parsed_result = json.loads(result)
                    logger.info(f"Parsed JSON result: {json.dumps(parsed_result, indent=2)}")
                    
                    # Validate response structure
                    if not isinstance(parsed_result, dict):
                        raise ValueError("Response is not a dictionary")
                    
                    if "tasks" not in parsed_result or not isinstance(parsed_result["tasks"], list):
                        raise ValueError("Response missing tasks array")
                    
                    # Ensure each task has required fields and format dates
                    for task in parsed_result["tasks"]:
                        if not isinstance(task, dict):
                            raise ValueError("Task is not a dictionary")
                        
                        required_fields = ["title", "due_date", "priority"]
                        missing_fields = [field for field in required_fields if field not in task]
                        if missing_fields:
                            raise ValueError(f"Task missing required fields: {missing_fields}")
                        
                        # Validate priority
                        if task["priority"] not in ["high", "medium", "low"]:
                            task["priority"] = "medium"  # Default to medium if invalid
                        
                        # Format or validate date
                        if task["due_date"] and task["due_date"].lower() not in ["today", "tomorrow", "asap"]:
                            try:
                                parsed_date = parse_due_date(task["due_date"])
                                task["due_date"] = parsed_date.strftime("%Y-%m-%d") if parsed_date else None
                            except ValueError:
                                task["due_date"] = None  # Set to None if date parsing fails
                    
                    return parsed_result
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                    return {"tasks": [], "suggested_reply": None}
                
                except ValueError as e:
                    logger.error(f"Invalid response format: {e}")
                    return {"tasks": [], "suggested_reply": None}
                
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    logger.error(f"OpenAI API error after all retries: {e}")
                    return {"tasks": [], "suggested_reply": None}
                logger.warning(f"OpenAI API error, retrying ({retry_count}/{max_retries}): {e}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
        
        return {"tasks": [], "suggested_reply": None}
        
    except Exception as e:
        logger.error(f"Error in task extraction: {e}")
        return {"tasks": [], "suggested_reply": None}
