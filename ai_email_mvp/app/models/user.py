from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    oauth_token = Column(String)  # Store the Google OAuth token
    refresh_token = Column(String)  # Store the refresh token
    google_credentials = Column(JSON)
    token_expiry = Column(DateTime(timezone=True), nullable=True)  # Store token expiry time
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Tasks created by this user
    created_tasks = relationship("Task", foreign_keys="[Task.created_by]", back_populates="creator")
    # Tasks assigned to this user
    assigned_tasks = relationship("Task", foreign_keys="[Task.assigned_to]", back_populates="assignee")
    # Teams created by this user
    created_teams = relationship("Team", back_populates="creator")
    # Team memberships
    team_memberships = relationship("TeamMember", back_populates="user")
