from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timedelta

def get_calendar_service(credentials):
    """Create Google Calendar service"""
    return build('calendar', 'v3', credentials=credentials)

async def create_calendar_event(task_title: str, deadline: datetime, assignee_id: int):
    """Create a calendar event for a task"""
    # Get user's credentials from database
    # This is a placeholder - implement actual credential retrieval
    credentials = None  # get_user_credentials(assignee_id)
    
    if not credentials:
        return None
        
    service = get_calendar_service(credentials)
    
    # Create event 30 minutes before deadline
    start_time = deadline - timedelta(minutes=30)
    
    event = {
        'summary': f'Task Due: {task_title}',
        'description': f'Deadline for task: {task_title}',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': deadline.isoformat(),
            'timeZone': 'UTC',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                {'method': 'popup', 'minutes': 30},  # 30 minutes before
            ],
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event['id']
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return None

async def update_calendar_event(event_id: str, new_deadline: datetime):
    """Update an existing calendar event"""
    # Get user's credentials from database
    credentials = None  # get_user_credentials(user_id)
    
    if not credentials:
        return False
        
    service = get_calendar_service(credentials)
    
    try:
        # Get existing event
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Update times
        start_time = new_deadline - timedelta(minutes=30)
        event['start']['dateTime'] = start_time.isoformat()
        event['end']['dateTime'] = new_deadline.isoformat()
        
        # Update event
        service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event
        ).execute()
        
        return True
    except Exception as e:
        print(f"Error updating calendar event: {e}")
        return False
