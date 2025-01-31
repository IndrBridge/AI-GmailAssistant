from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import json
import os
import pickle
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarClient:
    def __init__(self, credentials_dict: Dict[str, Any] = None):
        """Initialize the Calendar API client"""
        self.credentials = None
        if credentials_dict:
            self.credentials = Credentials.from_authorized_user_info(credentials_dict, SCOPES)
        self.service = None

    def _build_service(self):
        """Build and return Google Calendar service"""
        try:
            self.service = build('calendar', 'v3', credentials=self.credentials)
            return self.service
        except Exception as e:
            logger.error(f"Error building calendar service: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to Google Calendar")

    async def create_task_event(
        self,
        task_title: str,
        description: str,
        deadline: datetime,
        assignee_email: str,
        team_name: Optional[str] = None
    ) -> Optional[str]:
        """Create a calendar event for a task"""
        try:
            if not self.service:
                self._build_service()

            # Create event 30 minutes before deadline
            start_time = deadline - timedelta(minutes=30)
            
            event = {
                'summary': f'Task Due: {task_title}',
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': deadline.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [
                    {'email': assignee_email}
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},  # 30 minutes before
                    ],
                },
            }

            # Add team name to event details if provided
            if team_name:
                event['description'] = f"{description}\n\nTeam: {team_name}"

            event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'  # Send emails to attendees
            ).execute()

            logger.info(f"Calendar event created: {event.get('htmlLink')}")
            return event.get('id')

        except HttpError as error:
            logger.error(f"Error creating calendar event: {error}")
            if error.resp.status == 401:
                raise HTTPException(status_code=401, detail="Calendar authorization expired")
            raise HTTPException(status_code=500, detail="Failed to create calendar event")
        except Exception as e:
            logger.error(f"Unexpected error creating calendar event: {e}")
            raise HTTPException(status_code=500, detail="Failed to create calendar event")

    async def update_task_event(
        self,
        event_id: str,
        task_title: Optional[str] = None,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> bool:
        """Update an existing calendar event"""
        try:
            if not self.service:
                self._build_service()

            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            # Update event fields
            if task_title:
                event['summary'] = f'Task Due: {task_title}'
            
            if description:
                event['description'] = description

            if deadline:
                start_time = deadline - timedelta(minutes=30)
                event['start']['dateTime'] = start_time.isoformat()
                event['end']['dateTime'] = deadline.isoformat()

            # Add status to description
            if status:
                current_description = event.get('description', '')
                status_line = f"\nStatus: {status.upper()}"
                if "Status:" in current_description:
                    # Replace existing status
                    lines = current_description.split('\n')
                    updated_lines = [line for line in lines if not line.startswith("Status:")]
                    updated_lines.append(status_line)
                    event['description'] = '\n'.join(updated_lines)
                else:
                    # Add new status
                    event['description'] = current_description + status_line

            # Update event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendUpdates='all'  # Send emails to attendees
            ).execute()

            logger.info(f"Calendar event updated: {updated_event.get('htmlLink')}")
            return True

        except HttpError as error:
            logger.error(f"Error updating calendar event: {error}")
            if error.resp.status == 401:
                raise HTTPException(status_code=401, detail="Calendar authorization expired")
            raise HTTPException(status_code=500, detail="Failed to update calendar event")
        except Exception as e:
            logger.error(f"Unexpected error updating calendar event: {e}")
            raise HTTPException(status_code=500, detail="Failed to update calendar event")

    async def delete_task_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        try:
            if not self.service:
                self._build_service()

            self.service.events().delete(
                calendarId='primary',
                eventId=event_id,
                sendUpdates='all'  # Send cancellation emails
            ).execute()

            logger.info(f"Calendar event deleted: {event_id}")
            return True

        except HttpError as error:
            logger.error(f"Error deleting calendar event: {error}")
            if error.resp.status == 401:
                raise HTTPException(status_code=401, detail="Calendar authorization expired")
            raise HTTPException(status_code=500, detail="Failed to delete calendar event")
        except Exception as e:
            logger.error(f"Unexpected error deleting calendar event: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete calendar event")
