from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from .. import oauth, database, schemas

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Get database session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/oauth/callback")
async def oauth_callback(token_data: schemas.TokenRequest, db: Session = Depends(get_db)):
    """Handle OAuth callback with access token"""
    try:
        return await oauth.handle_oauth_callback(token_data.access_token, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/users/me")
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    try:
        credentials = oauth.verify_token(token)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        user = db.query(models.User).filter(models.User.email == credentials.sub).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
