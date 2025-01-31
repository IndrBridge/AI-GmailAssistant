from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    priority = Column(String)  # low, medium, high
    status = Column(String, default="pending")  # pending, in_progress, completed
    created_by = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    calendar_event_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])
    team = relationship("Team", back_populates="tasks")

class TaskHistory(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)  # created, updated, completed
    details = Column(Text, nullable=True)  # JSON string of changes
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task")
    user = relationship("User")
