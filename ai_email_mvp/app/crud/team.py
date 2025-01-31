from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import List, Optional

from app.models.team import Team, TeamMember
from app.models.task import Task, TaskHistory
from app.schemas import team as team_schema
from app.schemas.task import TaskCreate, TaskUpdate, TaskHistoryCreate

def create_team(db: Session, team: team_schema.TeamCreate, creator_id: int) -> Team:
    """Create a new team"""
    db_team = Team(
        name=team.name,
        description=team.description,
        created_by=creator_id
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

def get_team(db: Session, team_id: int) -> Optional[Team]:
    """Get a team by ID"""
    return db.query(Team).filter(Team.id == team_id).first()

def get_user_teams(db: Session, user_id: int) -> List[Team]:
    """Get all teams for a user"""
    return db.query(Team).join(TeamMember).filter(TeamMember.user_id == user_id).all()

def add_team_member(db: Session, team_id: int, user_id: int, role: str) -> bool:
    """Add a member to a team"""
    # Check if already a member
    existing = db.query(TeamMember).filter(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).first()
    if existing:
        return False
    
    member = TeamMember(team_id=team_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    return True

def create_task(db: Session, task: TaskCreate, user_id: int) -> Task:
    db_task = Task(
        title=task.title,
        description=task.description,
        thread_id=task.thread_id,
        email_id=task.email_id,
        created_by=user_id,
        assigned_to=task.assigned_to,
        team_id=task.team_id,
        status=task.status,
        priority=task.priority,
        deadline=task.deadline
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: int, task_update: TaskUpdate, user_id: int) -> Optional[Task]:
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        return None

    # Track status change
    if task_update.status and task_update.status != db_task.status:
        history = TaskHistory(
            task_id=task_id,
            changed_by=user_id,
            old_status=db_task.status,
            new_status=task_update.status,
            notes=task_update.notes
        )
        db.add(history)

    # Update task fields
    for field, value in task_update.dict(exclude_unset=True).items():
        setattr(db_task, field, value)
    
    if task_update.status == "completed":
        db_task.completion_date = datetime.utcnow()
    
    db.commit()
    db.refresh(db_task)
    return db_task

def get_user_tasks(
    db: Session,
    user_id: int,
    status: Optional[str] = None,
    team_id: Optional[int] = None
) -> List[Task]:
    query = db.query(Task).filter(
        Task.assigned_to == user_id
    )
    
    if status:
        query = query.filter(Task.status == status)
    if team_id:
        query = query.filter(Task.team_id == team_id)
        
    return query.order_by(Task.deadline).all()

def get_team_tasks(
    db: Session,
    team_id: int,
    status: Optional[str] = None
) -> List[Task]:
    query = db.query(Task).filter(Task.team_id == team_id)
    
    if status:
        query = query.filter(Task.status == status)
        
    return query.order_by(Task.deadline).all()

def get_task_history(db: Session, task_id: int) -> List[TaskHistory]:
    return db.query(TaskHistory).filter(
        TaskHistory.task_id == task_id
    ).order_by(TaskHistory.timestamp.desc()).all()

def update_team(db: Session, team_id: int, team: team_schema.TeamUpdate) -> Optional[Team]:
    """Update a team"""
    db_team = get_team(db, team_id)
    if not db_team:
        return None
    
    for field, value in team.dict(exclude_unset=True).items():
        setattr(db_team, field, value)
    
    db.commit()
    db.refresh(db_team)
    return db_team
