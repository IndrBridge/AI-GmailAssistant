from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from datetime import datetime
from typing import List, Optional
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class GmailNotifier:
    def __init__(self, credentials_dict: dict):
        """Initialize Gmail API client"""
        self.credentials = Credentials.from_authorized_user_info(credentials_dict, ['https://www.googleapis.com/auth/gmail.send'])
        self.service = None

    def _build_service(self):
        """Build and return Gmail service"""
        try:
            self.service = build('gmail', 'v1', credentials=self.credentials)
            return self.service
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to Gmail")

    def _create_message(
        self,
        sender: str,
        to: str,
        subject: str,
        message_text: str,
        cc: Optional[List[str]] = None
    ) -> dict:
        """Create an email message"""
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        
        if cc:
            message['cc'] = ', '.join(cc)

        msg = MIMEText(message_text, 'html')
        message.attach(msg)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}

    async def send_task_notification(
        self,
        task_data: dict,
        action: str,
        sender_email: str,
        recipient_email: str,
        team_members: Optional[List[str]] = None
    ):
        """Send task-related email notification"""
        try:
            if not self.service:
                self._build_service()

            # Create email content based on action
            subject, body = self._get_notification_content(task_data, action)
            
            # Add team members as CC if provided
            cc_list = team_members if team_members else None

            # Create and send message
            message = self._create_message(
                sender=sender_email,
                to=recipient_email,
                subject=subject,
                message_text=body,
                cc=cc_list
            )

            self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            logger.info(f"Notification email sent to {recipient_email}")
            return True

        except HttpError as error:
            logger.error(f"Error sending notification: {error}")
            if error.resp.status == 401:
                raise HTTPException(status_code=401, detail="Gmail authorization expired")
            raise HTTPException(status_code=500, detail="Failed to send notification")
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}")
            raise HTTPException(status_code=500, detail="Failed to send notification")

    def _get_notification_content(self, task_data: dict, action: str) -> tuple:
        """Generate email subject and body based on action"""
        deadline = datetime.fromisoformat(task_data['deadline']) if task_data.get('deadline') else None
        deadline_str = deadline.strftime("%Y-%m-%d %H:%M") if deadline else "No deadline"
        
        # Get priority label
        priority_labels = {1: "High", 2: "Medium", 3: "Low"}
        priority = priority_labels.get(task_data.get('priority', 3), "Normal")

        if action == "created":
            subject = f"New Task Assigned: {task_data['title']}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>New Task Assignment</h2>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                    <p><strong>Task:</strong> {task_data['title']}</p>
                    <p><strong>Due Date:</strong> {deadline_str}</p>
                    <p><strong>Priority:</strong> {priority}</p>
                    <p><strong>Description:</strong><br>
                    {task_data.get('description', 'No description provided')}</p>
                </div>
                <p>Please review and update the status accordingly.</p>
                <p style="color: #666;">This task has been added to your Google Calendar with reminders.</p>
            </body>
            </html>
            """

        elif action == "completed":
            subject = f"Task Completed: {task_data['title']}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>Task Completed</h2>
                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px;">
                    <p><strong>Task:</strong> {task_data['title']}</p>
                    <p><strong>Completed on:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}</p>
                    <p><strong>Original Due Date:</strong> {deadline_str}</p>
                </div>
                <p>Great job! The task has been marked as completed.</p>
            </body>
            </html>
            """

        elif action in ["accepted", "rejected"]:
            status_color = "#e8f5e9" if action == "accepted" else "#ffebee"
            subject = f"Task {action.capitalize()}: {task_data['title']}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>Task Status Update</h2>
                <div style="background-color: {status_color}; padding: 15px; border-radius: 5px;">
                    <p><strong>Task:</strong> {task_data['title']}</p>
                    <p><strong>Status:</strong> {action.capitalize()}</p>
                    <p><strong>Due Date:</strong> {deadline_str}</p>
                    <p><strong>Priority:</strong> {priority}</p>
                </div>
                <p>The task status has been updated to {action}.</p>
                {
                    "The task has been added to your calendar." if action == "accepted"
                    else "The task has been removed from consideration."
                }
            </body>
            </html>
            """

        elif action == "reminder":
            subject = f"Task Reminder: {task_data['title']}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>Task Reminder</h2>
                <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px;">
                    <p><strong>Task:</strong> {task_data['title']}</p>
                    <p><strong>Due Date:</strong> {deadline_str}</p>
                    <p><strong>Priority:</strong> {priority}</p>
                    <p><strong>Description:</strong><br>
                    {task_data.get('description', 'No description provided')}</p>
                </div>
                <p>This is a reminder about your upcoming task deadline.</p>
                <p>Please update the task status if you've made progress.</p>
            </body>
            </html>
            """

        else:
            subject = f"Task Update: {task_data['title']}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>Task Update</h2>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                    <p><strong>Task:</strong> {task_data['title']}</p>
                    <p><strong>Status:</strong> {action.capitalize()}</p>
                    <p><strong>Due Date:</strong> {deadline_str}</p>
                </div>
                <p>The task has been updated.</p>
            </body>
            </html>
            """

        return subject, body
