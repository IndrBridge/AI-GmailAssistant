from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from datetime import datetime
from app import crud

async def send_task_notification(task_id: int, action: str):
    """Send email notification for task updates"""
    # Get task details from database
    # This is a placeholder - implement actual database queries
    task = None  # crud.team.get_task(db, task_id)
    if not task:
        return
        
    # Get assignee email
    assignee_email = None  # get_user_email(task.assigned_to)
    if not assignee_email:
        return

    # Create email content based on action
    subject = ""
    body = ""
    
    if action == "created":
        subject = f"New Task Assigned: {task.title}"
        body = f"""
        You have been assigned a new task:
        
        Title: {task.title}
        Description: {task.description}
        Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M')} UTC
        
        Please review and update the status accordingly.
        """
    
    elif action == "completed":
        subject = f"Task Completed: {task.title}"
        body = f"""
        Task has been marked as completed:
        
        Title: {task.title}
        Completed on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
        
        Great job!
        """
    
    elif action in ["accepted", "rejected"]:
        subject = f"Task {action.capitalize()}: {task.title}"
        body = f"""
        Task status has been updated to {action}:
        
        Title: {task.title}
        Updated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
        """

    # Send email
    try:
        msg = MIMEMultipart()
        msg['From'] = "your-email@gmail.com"  # Update with your email
        msg['To'] = assignee_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # This is a placeholder - implement actual email sending
        # server = smtplib.SMTP('smtp.gmail.com', 587)
        # server.starttls()
        # server.login("your-email@gmail.com", "your-password")
        # server.send_message(msg)
        # server.quit()
        
        print(f"Email notification sent to {assignee_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email notification: {e}")
        return False
