from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/email/{email}")
async def get_user_by_email(
    email: str,
    db: Session = Depends(get_db)
):
    """Get user by email"""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
