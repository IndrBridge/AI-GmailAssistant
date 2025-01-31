from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.team import Team, TeamCreate, TeamUpdate, TeamMember, TeamMemberCreate
from app import crud

router = APIRouter(prefix="/api/teams", tags=["teams"])

@router.post("/", response_model=Team)
async def create_team(
    team: TeamCreate,
    db: Session = Depends(get_db)
):
    """Create a new team"""
    # Get user by email
    user = crud.get_user_by_email(db, team.created_by)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db_team = crud.create_team(db, team, user.id)
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team"
        )
    
    return db_team

@router.get("/user/{email}", response_model=List[Team])
async def get_user_teams(
    email: str,
    db: Session = Depends(get_db)
):
    """Get all teams for a user"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_user_teams(db, user.id)

@router.post("/{team_id}/members", response_model=TeamMember)
async def add_team_member(
    team_id: int,
    member: TeamMemberCreate,
    db: Session = Depends(get_db)
):
    """Add a member to a team"""
    # Get user by email
    user = crud.get_user_by_email(db, member.user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    success = crud.add_team_member(db, team_id, user.id, member.role)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member"
        )
    
    return {"team_id": team_id, "user_id": user.id, "role": member.role}

@router.get("/{team_id}/tasks")
async def get_team_tasks(
    team_id: int,
    db: Session = Depends(get_db)
):
    """Get all tasks for a team"""
    team = crud.get_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    return crud.get_team_tasks(db, team_id)

@router.put("/{team_id}", response_model=Team)
async def update_team(
    team_id: int,
    team: TeamUpdate,
    db: Session = Depends(get_db)
):
    """Update a team"""
    db_team = crud.get_team(db, team_id)
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    return crud.update_team(db, team_id, team)
