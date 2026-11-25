from .models import Notification


def create_notification(*, recipient, title, body="", announcement=None):
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        announcement=announcement,
    )
