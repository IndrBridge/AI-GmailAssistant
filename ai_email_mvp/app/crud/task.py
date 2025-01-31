from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import List, Optional

from app.models.task import Task, TaskHistory
from app.models.user import User
from app.schemas import task as task_schema

def create_task(db: Session, task: task_schema.TaskCreate) -> Task:
    """Create a new task"""
    # Get creator by email
    creator = db.query(User).filter(User.email == task.created_by).first()
    if not creator:
        return None
    
    # Get assignee by email if provided
    assignee_id = None
    if task.assigned_to:
        assignee = db.query(User).filter(User.email == task.assigned_to).first()
        if assignee:
            assignee_id = assignee.id
    
    # Create task
    db_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority.value,
        deadline=task.deadline,
        team_id=task.team_id,
        created_by=creator.id,
        assigned_to=assignee_id,
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task(db: Session, task_id: int) -> Optional[Task]:
    """Get a task by ID"""
    return db.query(Task).filter(Task.id == task_id).first()

def get_user_tasks(db: Session, user_email: str) -> List[Task]:
    """Get all tasks for a user"""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    return db.query(Task).filter(
        or_(Task.created_by == user.id, Task.assigned_to == user.id)
    ).all()

def update_task(db: Session, task_id: int, task: task_schema.TaskUpdate) -> Optional[Task]:
    """Update a task"""
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    
    # Get updater by email
    updater = db.query(User).filter(User.email == task.updated_by).first()
    if not updater:
        return None
    
    # Update task fields
    for field, value in task.dict(exclude_unset=True).items():
        if field == "updated_by":
            continue
        if isinstance(value, task_schema.TaskStatus):
            value = value.value
        if isinstance(value, task_schema.TaskPriority):
            value = value.value
        setattr(db_task, field, value)
    
    # Add history entry
    history = TaskHistory(
        task_id=task_id,
        user_id=updater.id,
        action="updated",
        details="Task updated"
    )
    db.add(history)
    
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task_history(db: Session, task_id: int) -> List[TaskHistory]:
    """Get history for a task"""
    return db.query(TaskHistory).filter(TaskHistory.task_id == task_id).all()

def get_task_analytics(db: Session, user_email: str):
    """Get task analytics for a user"""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return None
    
    total_tasks = db.query(Task).filter(
        or_(Task.created_by == user.id, Task.assigned_to == user.id)
    ).count()
    
    completed_tasks = db.query(Task).filter(
        and_(
            or_(Task.created_by == user.id, Task.assigned_to == user.id),
            Task.status == "completed"
        )
    ).count()
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
    }

def get_upcoming_tasks(db: Session, user_email: str, days: int = 7) -> List[Task]:
    """Get upcoming tasks for a user"""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    deadline = datetime.now() + timedelta(days=days)
    return db.query(Task).filter(
        and_(
            or_(Task.created_by == user.id, Task.assigned_to == user.id),
            Task.deadline <= deadline,
            Task.status != "completed"
        )
    ).all()

def get_overdue_tasks(db: Session, user_email: str) -> List[Task]:
    """Get overdue tasks for a user"""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    now = datetime.now()
    return db.query(Task).filter(
        and_(
            or_(Task.created_by == user.id, Task.assigned_to == user.id),
            Task.deadline < now,
            Task.status != "completed"
        )
    ).all()
