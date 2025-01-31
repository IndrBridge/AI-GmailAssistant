import logging
from datetime import datetime
import asyncio
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from sqlalchemy.orm import Session
from . import crud, models
from .database import SessionLocal
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email configuration
mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

fastmail = FastMail(mail_config)

async def send_reminder_email(task: models.Task):
    """Send a reminder email for a task."""
    try:
        message = MessageSchema(
            subject=f"Reminder: {task.title}",
            recipients=[task.user.email],
            subtype="html",  # Required field for FastMail
            body=f"""
            Hi {task.user.email},

            This is a reminder for your task: {task.title}

            Due date: {task.due_date.strftime('%Y-%m-%d %H:%M %Z') if task.due_date else 'Not set'}
            Priority: {task.priority}
            Status: {task.status}

            Description:
            {task.description or 'No description provided'}

            You can view and update this task in your Gmail Assistant.

            Best regards,
            Gmail Assistant
            """
        )
        await fastmail.send_message(message)
        logger.info(f"Sent reminder email for task {task.id} to {task.user.email}")
    except Exception as e:
        logger.error(f"Error sending reminder email for task {task.id}: {e}")
        raise

async def process_due_reminders():
    """Process all due reminders and send emails."""
    try:
        db = SessionLocal()
        due_tasks = crud.get_due_reminders(db)
        
        for task in due_tasks:
            # Send reminder email
            await send_reminder_email(task)
            # Mark reminder as sent
            crud.mark_reminder_sent(db, task.id)
                
    except Exception as e:
        logger.error(f"Error processing reminders: {e}")
    finally:
        db.close()

async def reminder_background_task():
    """Background task that runs continuously to check and send reminders."""
    while True:
        await process_due_reminders()
        # Wait for 1 minute before checking again
        await asyncio.sleep(60)
