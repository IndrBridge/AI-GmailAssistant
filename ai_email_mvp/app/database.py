from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# Configure logging
logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    from . import models  # Import models here to avoid circular imports
    Base.metadata.drop_all(bind=engine)  # Drop all tables
    Base.metadata.create_all(bind=engine)  # Create new tables
