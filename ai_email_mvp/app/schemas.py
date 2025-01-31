from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from dateutil import tz
from pytz import UTC

class TaskPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    deleted = "deleted"

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.medium
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None

    @validator('due_date', pre=True)
    def parse_due_date(cls, v):
        if v is None:
            return None
            
        if isinstance(v, datetime):
            return v
            
        if isinstance(v, str):
            from main import parse_due_date
            result = parse_due_date(v)
            if result is None:
                raise ValueError(f"Could not parse date string: {v}")
            return result
            
        raise ValueError(f"Expected string or datetime, got {type(v)}")

class TaskCreate(TaskBase):
    email_id: Optional[int] = None
    user_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None

    @validator("reminder_time")
    def validate_reminder_time(cls, v):
        if v is None:
            return v

        if v.tzinfo is None:
            raise ValueError("Reminder time must be timezone-aware")
        
        now = datetime.now(tz.tzutc())
        v_utc = v.astimezone(tz.tzutc())
        
        if v_utc <= now:
            raise ValueError("Reminder time must be in the future")
        return v_utc

class Task(TaskBase):
    id: int
    user_id: int
    email_id: Optional[int] = None
    status: TaskStatus = TaskStatus.pending
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EmailBase(BaseModel):
    gmail_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    content: str
    thread_id: Optional[str] = None
    received_at: datetime

class EmailCreate(EmailBase):
    user_id: Optional[int] = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Email(EmailBase):
    id: int
    user_id: int
    suggested_reply: Optional[str] = None
    created_at: datetime
    tasks: List[Task] = []

    class Config:
        from_attributes = True

# Reminder schemas
class ReminderCreate(BaseModel):
    reminder_time: datetime
    
    @validator("reminder_time")
    def validate_reminder_time(cls, v: datetime):
        if v.tzinfo is None:
            raise ValueError("Reminder time must be timezone-aware")
        
        now = datetime.now(tz.tzutc())
        v_utc = v.astimezone(tz.tzutc())
        
        if v_utc <= now:
            raise ValueError("Reminder time must be in the future")
        return v_utc

class ReminderUpdate(BaseModel):
    reminder_time: Optional[datetime] = None

# Current Email Processing schemas
class CurrentEmailProcess(BaseModel):
    gmail_id: str
    thread_id: str
    subject: str
    sender: str
    content: str

class CurrentEmailReply(BaseModel):
    gmail_id: str
    content: str
    context: Optional[str] = None

class EmailProcessResponse(BaseModel):
    tasks: List[Task]
    suggested_reply: Optional[str]
    summary: Optional[str]

class EmailReplyResponse(BaseModel):
    suggested_reply: str
    tone: str
    key_points_addressed: List[str]

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    oauth_token: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    oauth_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None

    @validator('oauth_token')
    def oauth_token_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('oauth_token must not be empty')
        return v.strip()

class User(UserBase):
    id: int
    oauth_token: str
    created_at: datetime
    updated_at: datetime
    tasks: List[Task] = []
    emails: List[Email] = []

    class Config:
        from_attributes = True

class TaskFilter(BaseModel):
    status: Optional[List[TaskStatus]] = None
    priority: Optional[List[TaskPriority]] = None
    due_date_start: Optional[datetime] = None
    due_date_end: Optional[datetime] = None
    search_query: Optional[str] = None
