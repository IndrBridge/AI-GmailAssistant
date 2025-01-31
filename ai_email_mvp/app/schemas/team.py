from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TeamRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class TaskStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None

class TeamCreate(TeamBase):
    created_by: EmailStr  # Email address of the user creating the team

class TeamUpdate(TeamBase):
    pass

class Team(TeamBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TeamMemberBase(BaseModel):
    role: TeamRole = TeamRole.MEMBER

class TeamMemberCreate(TeamMemberBase):
    user_email: EmailStr

class TeamMember(TeamMemberBase):
    id: int
    team_id: int
    user_id: int
    joined_at: datetime

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    thread_id: str
    email_id: str
    team_id: Optional[int] = None
    priority: Optional[int] = 1
    deadline: Optional[datetime] = None

class TaskCreate(TaskBase):
    assigned_to: Optional[int] = None

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    assigned_to: Optional[int] = None
    deadline: Optional[datetime] = None
    priority: Optional[int] = None
    completion_date: Optional[datetime] = None
    calendar_event_id: Optional[str] = None

class Task(TaskBase):
    id: int
    created_by: int
    assigned_to: Optional[int]
    status: TaskStatus
    completion_date: Optional[datetime]
    calendar_event_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskHistoryBase(BaseModel):
    task_id: int
    old_status: Optional[str]
    new_status: str
    notes: Optional[str]

class TaskHistoryCreate(TaskHistoryBase):
    pass

class TaskHistory(TaskHistoryBase):
    id: int
    changed_by: int
    timestamp: datetime

    class Config:
        from_attributes = True
