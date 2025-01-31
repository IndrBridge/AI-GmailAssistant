from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os
from dotenv import load_dotenv
import json
import logging
import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from . import crud, models, schemas, auth

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# OAuth 2.0 configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]

def create_oauth_flow(redirect_uri: str, state=None):
    """Create a Google OAuth flow."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = redirect_uri
    return flow

def get_oauth_url(redirect_uri: str):
    """Get the Google OAuth URL."""
    try:
        flow = create_oauth_flow(redirect_uri)
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url
    except Exception as e:
        logger.error(f"Error creating OAuth URL: {e}")
        raise

async def handle_oauth_callback(oauth_token: str, db: Session):
    """Handle the OAuth callback with access token."""
    try:
        logger.info("Starting OAuth callback handler")
        
        if not oauth_token:
            logger.error("No OAuth token provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth token not provided"
            )
            
        logger.info("Creating credentials with token")
        # Create credentials from the access token
        credentials = Credentials(
            token=oauth_token,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES
        )

        logger.info("Getting user info")
        # Get user info
        user_info = await get_user_info(credentials)
        
        if not user_info:
            logger.error("Failed to get user info from Google")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
            
        if 'email' not in user_info:
            logger.error("No email in user info")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No email in user info from Google"
            )

        logger.info(f"Creating/updating user with email: {user_info['email']}")
        # Create or update user in database
        user_create = schemas.UserCreate(
            email=user_info['email'],
            oauth_token=oauth_token
        )
        
        db_user = crud.get_user_by_email(db, email=user_info['email'])
        if not db_user:
            db_user = crud.create_user(db, user=user_create)
        
        logger.info("Creating access token")
        # Create access token
        access_token = auth.create_access_token(data={"sub": db_user.email})
        
        logger.info("OAuth callback completed successfully")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": db_user
        }

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

async def get_user_info(credentials: Credentials):
    """Get user info from Google using credentials."""
    try:
        # Use requests directly with the token
        headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get user info. Status: {response.status_code}, Response: {response.text}")
            return None
            
        user_info = response.json()
        logger.info(f"Successfully got user info for: {user_info.get('email')}")
        return user_info
        
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return None

def refresh_credentials(credentials: Credentials) -> Credentials:
    """Refresh Google OAuth credentials if expired."""
    try:
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
        return credentials
    except Exception as e:
        logger.error(f"Error refreshing credentials: {e}")
        raise
