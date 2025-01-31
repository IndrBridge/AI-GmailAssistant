from sqlalchemy.orm import Session
from app.models.user import User  # Import directly from module
from app.schemas.user import UserCreate, UserUpdate
from typing import Optional, List

def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        name=user.name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user: UserUpdate) -> Optional[User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    for field, value in user.dict(exclude_unset=True).items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user
