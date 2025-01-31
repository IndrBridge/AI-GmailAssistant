from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Optional[datetime] = None
    team_id: Optional[int] = None

class TaskCreate(TaskBase):
    user_id: int  # ID of the creator
    assigned_to: Optional[int] = None  # ID of the assignee

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    deadline: Optional[datetime] = None
    team_id: Optional[int] = None
    assigned_to: Optional[int] = None

class TaskHistory(BaseModel):
    id: int
    task_id: int
    user_id: int
    action: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class Task(TaskBase):
    id: int
    created_by: int
    assigned_to: Optional[int] = None
    status: TaskStatus = TaskStatus.PENDING
    completion_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
