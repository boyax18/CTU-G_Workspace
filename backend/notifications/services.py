# notifications/services.py
from .models import Notification


def notify(user_ids, message, link=""):
    """Create one notification per unique recipient id."""
    unique_ids = set(user_ids)
    Notification.objects.bulk_create([
        Notification(recipient_id=uid, message=message, link=link)
        for uid in unique_ids
    ])