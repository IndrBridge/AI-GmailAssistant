from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas.task import Task, TaskCreate, TaskUpdate, TaskHistory
from app import crud
from sqlalchemy import func, or_, case
from sqlalchemy.exc import SQLAlchemyError
from app.services.google_calendar import GoogleCalendarClient
from app.services.gmail_notifier import GmailNotifier

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

def get_calendar_client():
    return GoogleCalendarClient()

def get_gmail_notifier():
    return GmailNotifier()

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    email: str,
    db: Session = Depends(get_db)
):
    """Create a new task"""
    # Get creator by email
    creator = crud.get_user_by_email(db, email)
    if not creator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator not found"
        )
    
    # Get assignee by email if provided
    assignee_id = None
    if task.assigned_to:
        assignee = crud.get_user_by_email(db, task.assigned_to)
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignee not found"
            )
        assignee_id = assignee.id
    
    task_dict = task.dict()
    task_dict["created_by"] = creator.id
    task_dict["assigned_to"] = assignee_id
    
    return crud.create_task(db, task_dict)

@router.get("/user/{email}", response_model=List[Task])
async def get_user_tasks(
    email: str,
    db: Session = Depends(get_db)
):
    """Get all tasks for a user"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_user_tasks(db, user.id)

@router.get("/{task_id}/history", response_model=List[TaskHistory])
async def get_task_history(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get history for a task"""
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return crud.get_task_history(db, task_id)

@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    email: str,
    db: Session = Depends(get_db)
):
    """Update a task"""
    # Check if task exists
    db_task = crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Get user by email
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is task creator or assignee
    if user.id != db_task.created_by and user.id != db_task.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update task"
        )
    
    return crud.update_task(db, task_id, task, user.id)

@router.put("/{task_id}/complete", response_model=Task)
async def complete_task(
    task_id: int,
    email: str,
    db: Session = Depends(get_db)
):
    """Complete a task"""
    # Check if task exists
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Get user by email
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is task creator or assignee
    if user.id != task.created_by and user.id != task.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete task"
        )
    
    task.status = "completed"
    task.completion_date = datetime.now()
    
    return crud.update_task(db, task_id, task, user.id)

@router.get("/analytics", response_model=dict)
async def get_task_analytics(
    email: str,
    db: Session = Depends(get_db)
):
    """Get task analytics for a user"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_task_analytics(db, user.id)

@router.get("/upcoming", response_model=List[Task])
async def get_upcoming_tasks(
    email: str,
    db: Session = Depends(get_db)
):
    """Get upcoming tasks for a user"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_upcoming_tasks(db, user.id)

@router.get("/overdue", response_model=List[Task])
async def get_overdue_tasks(
    email: str,
    db: Session = Depends(get_db)
):
    """Get overdue tasks for a user"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_overdue_tasks(db, user.id)

@router.post("/{task_id}/reminder", response_model=dict)
async def set_task_reminder(
    task_id: int,
    email: str,
    reminder_time: datetime,
    db: Session = Depends(get_db)
):
    """Set a reminder for a task"""
    # Check if task exists
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Get user by email
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is task creator or assignee
    if user.id != task.created_by and user.id != task.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to set reminder"
        )
    
    return crud.set_task_reminder(db, task_id, user.id, reminder_time)

@router.get("/reminders", response_model=List[dict])
async def get_task_reminders(
    email: str,
    db: Session = Depends(get_db)
):
    """Get all task reminders for a user"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_task_reminders(db, user.id)

@router.get("/filter", response_model=List[Task])
async def filter_tasks(
    email: str,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    team_id: Optional[int] = None,
    assigned_to: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Filter tasks based on various criteria"""
    try:
        user = crud.get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        query = db.query(Task)

        # Base filters
        query = query.filter(
            or_(
                Task.created_by == user.id,
                Task.assigned_to == user.id,
                Task.team_id.in_(
                    db.query(TeamMember.team_id)
                    .filter(TeamMember.user_id == user.id)
                    .subquery()
                )
            )
        )

        # Apply filters
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if team_id:
            query = query.filter(Task.team_id == team_id)
        if assigned_to:
            assignee = crud.get_user_by_email(db, assigned_to)
            if not assignee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assignee not found"
                )
            query = query.filter(Task.assigned_to == assignee.id)
        if due_before:
            query = query.filter(Task.deadline <= due_before)
        if due_after:
            query = query.filter(Task.deadline >= due_after)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term)
                )
            )

        # Order by deadline and priority
        query = query.order_by(Task.deadline.asc(), Task.priority.asc())

        return query.all()

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/analytics", response_model=dict)
async def get_task_analytics(
    email: str,
    team_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get task analytics and statistics"""
    try:
        user = crud.get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        # Set default date range if not provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Base query filters
        base_filters = []
        if team_id:
            base_filters.append(Task.team_id == team_id)
        else:
            base_filters.append(
                or_(
                    Task.created_by == user.id,
                    Task.assigned_to == user.id,
                    Task.team_id.in_(
                        db.query(TeamMember.team_id)
                        .filter(TeamMember.user_id == user.id)
                        .subquery()
                    )
                )
            )
        
        base_filters.extend([
            Task.created_at >= start_date,
            Task.created_at <= end_date
        ])

        # Task completion rate
        total_tasks = db.query(func.count(Task.id)).filter(*base_filters).scalar()
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.status == "completed",
            *base_filters
        ).scalar()
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Average completion time
        avg_completion_time = db.query(
            func.avg(Task.completion_date - Task.created_at)
        ).filter(
            Task.status == "completed",
            *base_filters
        ).scalar()

        # Tasks by priority
        priority_distribution = db.query(
            Task.priority,
            func.count(Task.id)
        ).filter(
            *base_filters
        ).group_by(Task.priority).all()

        # Tasks by status
        status_distribution = db.query(
            Task.status,
            func.count(Task.id)
        ).filter(
            *base_filters
        ).group_by(Task.status).all()

        # Overdue tasks
        overdue_tasks = db.query(func.count(Task.id)).filter(
            Task.deadline < datetime.utcnow(),
            Task.status != "completed",
            *base_filters
        ).scalar()

        # Tasks completed on time
        on_time_tasks = db.query(func.count(Task.id)).filter(
            Task.status == "completed",
            Task.completion_date <= Task.deadline,
            *base_filters
        ).scalar()

        # Team member performance (if team_id provided)
        team_performance = None
        if team_id:
            team_performance = db.query(
                Task.assigned_to,
                func.count(Task.id).label('total_tasks'),
                func.sum(case([(Task.status == 'completed', 1)], else_=0)).label('completed_tasks'),
                func.avg(case([(Task.status == 'completed', Task.completion_date - Task.created_at)], else_=None)).label('avg_completion_time')
            ).filter(
                Task.team_id == team_id,
                *base_filters
            ).group_by(Task.assigned_to).all()

        return {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "task_metrics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": round(completion_rate, 2),
                "avg_completion_time": str(avg_completion_time) if avg_completion_time else None,
                "overdue_tasks": overdue_tasks,
                "on_time_completions": on_time_tasks
            },
            "distributions": {
                "priority": {p: c for p, c in priority_distribution},
                "status": {s: c for s, c in status_distribution}
            },
            "team_performance": [
                {
                    "user_id": user_id,
                    "total_tasks": total,
                    "completed_tasks": completed,
                    "completion_rate": round((completed / total * 100), 2) if total > 0 else 0,
                    "avg_completion_time": str(avg_time) if avg_time else None
                }
                for user_id, total, completed, avg_time in (team_performance or [])
            ] if team_performance else None
        }

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/upcoming", response_model=List[Task])
async def get_upcoming_tasks(
    email: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get upcoming tasks due within specified days"""
    try:
        user = crud.get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        end_date = datetime.utcnow() + timedelta(days=days)
        
        query = db.query(Task).filter(
            Task.deadline <= end_date,
            Task.status != "completed",
            or_(
                Task.assigned_to == user.id,
                Task.team_id.in_(
                    db.query(TeamMember.team_id)
                    .filter(TeamMember.user_id == user.id)
                    .subquery()
                )
            )
        ).order_by(Task.deadline.asc(), Task.priority.asc())

        return query.all()

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/overdue", response_model=List[Task])
async def get_overdue_tasks(
    email: str,
    db: Session = Depends(get_db)
):
    """Get overdue tasks"""
    try:
        user = crud.get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        query = db.query(Task).filter(
            Task.deadline < datetime.utcnow(),
            Task.status != "completed",
            or_(
                Task.assigned_to == user.id,
                Task.team_id.in_(
                    db.query(TeamMember.team_id)
                    .filter(TeamMember.user_id == user.id)
                    .subquery()
                )
            )
        ).order_by(Task.deadline.asc(), Task.priority.asc())

        return query.all()

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/reminders", response_model=List[dict])
async def get_task_reminders(
    email: str,
    db: Session = Depends(get_db)
):
    """Get all task reminders for a user"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_task_reminders(db, user.id)
