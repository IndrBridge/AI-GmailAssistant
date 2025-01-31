class GoogleCalendarClient:
    """Minimal implementation of Google Calendar client for testing"""
    def __init__(self):
        pass

    async def create_event(self, task_id: int, title: str, description: str = None, start_time: str = None):
        """Create a calendar event for a task"""
        # For testing, just return a mock event ID
        return f"event_{task_id}"

    async def update_event(self, event_id: str, title: str, description: str = None, start_time: str = None):
        """Update a calendar event"""
        # For testing, just return True
        return True

    async def delete_event(self, event_id: str):
        """Delete a calendar event"""
        # For testing, just return True
        return True
