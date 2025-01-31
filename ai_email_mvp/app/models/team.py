from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base
import enum

class TeamRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class TaskStatus(str, enum.Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_teams")
    members = relationship("TeamMember", back_populates="team")
    tasks = relationship("Task", back_populates="team")

class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(Enum(TeamRole), default=TeamRole.MEMBER)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    thread_id = Column(String, index=True)
    email_id = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    status = Column(Enum(TaskStatus), default=TaskStatus.NEW)
    priority = Column(Integer, default=1)
    deadline = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    calendar_event_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tasks")
    team = relationship("Team", back_populates="tasks")
    history = relationship("TaskHistory", back_populates="task")

class TaskHistory(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    changed_by = Column(Integer, ForeignKey("users.id"))
    old_status = Column(Enum(TaskStatus))
    new_status = Column(Enum(TaskStatus))
    notes = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="history")
    user = relationship("User")
