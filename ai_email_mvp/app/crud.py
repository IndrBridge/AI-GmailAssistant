from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import or_
from datetime import timezone
import logging

logger = logging.getLogger(__name__)

# User operations
def get_user(db: Session, user_id: int):
    """Get a user by ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    """Get a user by email"""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user"""
    db_user = models.User(
        email=user.email,
        oauth_token=user.oauth_token,
        refresh_token=user.refresh_token
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user: schemas.UserCreate):
    """Update an existing user."""
    try:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            return None
            
        for key, value in user.dict().items():
            setattr(db_user, key, value)
            
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise

def get_user_by_id(db: Session, user_id: int):
    """Get a user by ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user_tokens(db: Session, user_id: int, oauth_token: str, refresh_token: Optional[str], token_expiry: Optional[datetime]):
    try:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            return None
        
        db_user.oauth_token = oauth_token
        if refresh_token:
            db_user.refresh_token = refresh_token
        if token_expiry:
            db_user.token_expiry = token_expiry
            
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        print(f"Error updating user tokens: {e}")
        raise

# Task operations
def create_task(db: Session, task: schemas.TaskCreate, user_id: int):
    try:
        # Create task directly without checking for email
        db_task = models.Task(
            title=task.title,
            description=task.description,
            priority=task.priority,
            due_date=task.due_date,
            user_id=user_id,
            email_id=task.email_id,
            status="pending"
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        print(f"Successfully created task: {db_task.title}")
        return db_task
    except Exception as e:
        db.rollback()
        print(f"Error creating task: {e}")
        raise

def get_task(db: Session, task_id: int):
    """Get a task by ID."""
    return db.query(models.Task).filter(models.Task.id == task_id).first()

def get_tasks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Task).filter(models.Task.user_id == user_id)\
        .offset(skip).limit(limit).all()

def get_tasks_filtered(db: Session, user_id: int, filter_params: schemas.TaskFilter) -> List[models.Task]:
    query = db.query(models.Task).filter(models.Task.user_id == user_id)
    
    if filter_params.status:
        query = query.filter(models.Task.status.in_(filter_params.status))
    
    if filter_params.priority:
        query = query.filter(models.Task.priority.in_(filter_params.priority))
    
    if filter_params.due_date_start:
        query = query.filter(models.Task.due_date >= filter_params.due_date_start)
    
    if filter_params.due_date_end:
        query = query.filter(models.Task.due_date <= filter_params.due_date_end)
    
    if filter_params.search_query:
        search = f"%{filter_params.search_query}%"
        query = query.filter(
            or_(
                models.Task.title.ilike(search),
                models.Task.description.ilike(search)
            )
        )
    
    return query.order_by(models.Task.due_date.asc()).all()

def get_user_tasks(db: Session, user_email: str, filter_params: Optional[schemas.TaskFilter] = None):
    """
    Get tasks for a user by their email address with optional filtering
    """
    try:
        # Get user by email
        user = get_user_by_email(db, user_email)
        if not user:
            return None
        
        # If filter params are provided, use filtered query
        if filter_params:
            return get_tasks_filtered(db, user.id, filter_params)
        
        # Otherwise, get all tasks for the user
        return get_tasks_by_user(db, user.id)
    except Exception as e:
        print(f"Error getting user tasks: {e}")
        raise

def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    """Update a task."""
    try:
        db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not db_task:
            return None
        
        update_data = task_update.dict(exclude_unset=True)
        
        # Convert reminder_time to UTC if it's provided
        if 'reminder_time' in update_data and update_data['reminder_time']:
            update_data['reminder_time'] = update_data['reminder_time'].astimezone(timezone.utc)
        
        for key, value in update_data.items():
            setattr(db_task, key, value)
            
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        db.rollback()
        raise

def create_test_task(db: Session, user_email: str):
    """Create a test task for testing filters"""
    try:
        # Get or create user
        user = get_user_by_email(db, user_email)
        if not user:
            user = create_user(db, schemas.UserCreate(email=user_email, oauth_token="test_token"))
        
        # Create test email with timestamp for uniqueness
        timestamp = int(datetime.utcnow().timestamp())
        email = create_email(db, schemas.EmailCreate(
            gmail_id=f"test_email_{timestamp}",
            content="Test email content",
            received_at=datetime.utcnow()
        ), user.id)
        
        # Create test tasks with different priorities and statuses
        tasks = []
        priorities = ["high", "medium", "low"]
        statuses = ["pending", "in_progress", "completed"]
        
        for i, (priority, status) in enumerate(zip(priorities, statuses)):
            # Calculate reminder time for pending tasks
            reminder_time = None
            if status == "pending":
                reminder_time = datetime.now(timezone.utc) + timedelta(hours=i+1)
            
            task = schemas.TaskCreate(
                title=f"Test task {i+1} ({priority} priority, {status})",
                description=f"Test description for {priority} priority task",
                email_id=str(email.id)
            )
            task_obj = create_task(db, task, user.id)
            
            # Update status and reminder
            update_task(db, task_obj.id, schemas.TaskUpdate(
                priority=priority,
                status=status,
                due_date=datetime.utcnow() + timedelta(days=i+1),
                reminder_time=reminder_time
            ))
            tasks.append(task_obj)
        
        return tasks
    except Exception as e:
        print(f"Error creating test tasks: {e}")
        db.rollback()
        raise

# Team operations
def create_team(db: Session, team: schemas.TeamCreate, user_id: int):
    """Create a new team"""
    try:
        db_team = models.Team(
            name=team.name,
            description=team.description,
            created_by=user_id
        )
        db.add(db_team)
        db.commit()
        db.refresh(db_team)
        
        # Add creator as team owner
        db_team_member = models.TeamMember(
            team_id=db_team.id,
            user_id=user_id,
            role=models.TeamRole.OWNER
        )
        db.add(db_team_member)
        db.commit()
        
        return db_team
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating team: {e}")
        raise

def get_team(db: Session, team_id: int):
    """Get a team by ID"""
    return db.query(models.Team).filter(models.Team.id == team_id).first()

def get_user_teams(db: Session, user_id: int):
    """Get all teams for a user"""
    return db.query(models.Team)\
        .join(models.TeamMember)\
        .filter(models.TeamMember.user_id == user_id)\
        .all()

def add_team_member(db: Session, team_id: int, user_email: str, role: str = "member"):
    """Add a member to a team"""
    try:
        # Get user by email
        user = get_user_by_email(db, user_email)
        if not user:
            return None

        # Check if user is already a member
        existing_member = get_team_member(db, team_id, user.id)
        if existing_member:
            return existing_member

        db_team_member = models.TeamMember(
            team_id=team_id,
            user_id=user.id,
            role=role
        )
        db.add(db_team_member)
        db.commit()
        db.refresh(db_team_member)
        return db_team_member
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding team member: {e}")
        raise

def get_team_member(db: Session, team_id: int, user_id: int):
    """Get a team member"""
    return db.query(models.TeamMember)\
        .filter(models.TeamMember.team_id == team_id)\
        .filter(models.TeamMember.user_id == user_id)\
        .first()

def get_team_tasks(db: Session, team_id: int):
    """Get all tasks for a team"""
    return db.query(models.Task)\
        .filter(models.Task.team_id == team_id)\
        .all()

def update_team(db: Session, team_id: int, team_update: schemas.TeamUpdate):
    """Update a team"""
    try:
        db_team = get_team(db, team_id)
        if not db_team:
            return None

        for key, value in team_update.dict(exclude_unset=True).items():
            setattr(db_team, key, value)

        db.commit()
        db.refresh(db_team)
        return db_team
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating team: {e}")
        raise

def delete_team(db: Session, team_id: int):
    """Delete a team"""
    try:
        db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not db_team:
            return None
        
        db.delete(db_team)
        db.commit()
        return db_team
    except Exception as e:
        db.rollback()
        raise

# Reminder operations
def get_tasks_with_reminders(db: Session, user_id: int):
    """Get all tasks with pending reminders for a user."""
    try:
        now = datetime.now(timezone.utc)  # Use timezone-aware datetime
        query = db.query(models.Task).filter(
            models.Task.user_id == user_id,
            models.Task.reminder_time.isnot(None),
            models.Task.reminder_time > now,
            models.Task.status.notin_(['completed', 'deleted'])
        )
        
        # Log the SQL query
        logger.info(f"SQL Query: {query.statement}")
        
        # Execute query and get results
        tasks = query.all()
        logger.info(f"Found {len(tasks)} tasks for user {user_id}")
        
        return tasks
        
    except Exception as e:
        logger.error(f"Error getting tasks with reminders for user {user_id}: {str(e)}")
        raise

def get_due_reminders(db: Session):
    """Get all tasks with due reminders across all users."""
    now = datetime.now(timezone.utc)
    return db.query(models.Task).filter(
        models.Task.reminder_time.isnot(None),
        models.Task.reminder_time <= now,
        models.Task.status.notin_(['completed', 'deleted'])
    ).all()

def mark_reminder_sent(db: Session, task_id: int):
    """Mark a reminder as sent by clearing the reminder_time."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        task.reminder_time = None
        db.commit()
    return task

# Email operations
def create_email(db: Session, email: schemas.EmailCreate, user_id: int):
    """Create a new email or update if exists."""
    try:
        # Check if email already exists
        existing_email = db.query(models.Email).filter(models.Email.gmail_id == email.gmail_id).first()
        
        if existing_email:
            # Update existing email
            email_data = email.dict(exclude={'user_id'})  # Exclude user_id from the update data
            for key, value in email_data.items():
                setattr(existing_email, key, value)
            db.commit()
            db.refresh(existing_email)
            return existing_email
            
        # Create new email if doesn't exist
        email_data = email.dict(exclude={'user_id'})  # Exclude user_id from creation data
        db_email = models.Email(**email_data, user_id=user_id)
        db.add(db_email)
        db.commit()
        db.refresh(db_email)
        return db_email
    except Exception as e:
        db.rollback()
        raise

def get_email(db: Session, gmail_id: str):
    return db.query(models.Email).filter(models.Email.gmail_id == gmail_id).first()

def get_emails_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Email).filter(models.Email.user_id == user_id)\
        .order_by(models.Email.received_at.desc())\
        .offset(skip).limit(limit).all()
