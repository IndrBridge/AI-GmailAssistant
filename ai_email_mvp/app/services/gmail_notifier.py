class GmailNotifier:
    """Minimal implementation of Gmail notifier for testing"""
    def __init__(self):
        pass

    async def send_task_notification(self, recipient_email: str, task_title: str, task_description: str = None):
        """Send a task notification email"""
        # For testing, just return True
        return True

    async def send_reminder(self, recipient_email: str, task_title: str, reminder_time: str):
        """Send a task reminder email"""
        # For testing, just return True
        return True
