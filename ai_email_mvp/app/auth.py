from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import crud, models
from .database import get_db
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-123")  # Use environment variable with fallback
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": int(expire.timestamp())})  # Convert to Unix timestamp
    logger.info(f"Creating token with expiration: {expire} (timestamp: {int(expire.timestamp())})")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the email."""
    try:
        logger.info(f"Verifying token: {token[:10]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Token payload: {payload}")
        
        email: str = payload.get("sub")
        if email is None:
            logger.error("No email in token payload")
            return None
            
        exp = payload.get("exp")
        if exp is None:
            logger.error("No expiration in token payload")
            return None
            
        # Check if token has expired
        now = int(datetime.now(timezone.utc).timestamp())
        logger.info(f"Token expiration check - Exp: {exp}, Now: {now}")
        
        if exp < now:
            logger.error(f"Token expired. Exp: {exp}, Now: {now}")
            return None
            
        logger.info(f"Token valid for email: {email}")
        return email
        
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in verify_token: {str(e)}")
        return None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """Get the current user from a JWT token."""
    logger.info("=== Validating user token ===")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        logger.info("Raw token received: " + token[:10] + "...")
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            logger.info("Removed Bearer prefix")
            
        # Verify token
        logger.info("Verifying token: " + token[:10] + "...")
        email = verify_token(token)
        if email is None:
            logger.error("Token verification failed")
            raise credentials_exception
            
        logger.info(f"Token verified for email: {email}")
            
        # Get user from database
        user = crud.get_user_by_email(db, email)
        if user is None:
            # If user doesn't exist, create them
            logger.info(f"User not found for email: {email}, creating new user")
            user = models.User(email=email)
            db.add(user)
            db.commit()
            db.refresh(user)
            
        logger.info("=== Token validation successful ===")
        return user
        
    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise credentials_exception

def create_google_token(email: str, oauth_token: str) -> str:
    """Create a JWT token from Google OAuth credentials."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email, "oauth_token": oauth_token},
        expires_delta=access_token_expires
    )
    return access_token

def get_token_from_header(authorization: str) -> Optional[str]:
    """Extract token from Authorization header."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token

def require_auth(authorization: str = Depends(oauth2_scheme)) -> str:
    """Dependency to require authentication."""
    token = get_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = verify_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email
