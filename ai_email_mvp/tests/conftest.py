import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User
from app.routers.task import get_calendar_client, get_gmail_notifier

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

@pytest.fixture
def test_db():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test user in database
    test_user = User(
        email="test@example.com",
        oauth_token="test_token",
        refresh_token="test_refresh_token"
    )
    test_db.add(test_user)
    test_db.commit()
    test_db.refresh(test_user)
    
    client = TestClient(app)
    yield client
    
    # Clean up
    app.dependency_overrides.clear()

@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "oauth_token": "test_token",
        "refresh_token": "test_refresh_token"
    }

@pytest.fixture
def test_team():
    return {
        "name": "Test Team",
        "description": "Test team description"
    }

@pytest.fixture
def test_task():
    return {
        "title": "Test Task",
        "description": "Test task description",
        "priority": "medium",
        "due_date": "2024-12-31T23:59:59Z"
    } 