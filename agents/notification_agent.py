from typing import Any

from agents.base import Agent
from backend.src.services.notification_service import NotificationService


class NotificationAgent(Agent):
    def __init__(self, notifier: NotificationService) -> None:
        self.notifier = notifier

    @property
    def name(self) -> str:
        return "notification_agent"

    def notify_status(
        self,
        *,
        user_id: str,
        application_id: str,
        status: str,
        submission_reference: str | None,
    ) -> dict[str, Any]:
        subject = f"Service Agent Update: {status}"
        message = (
            f"Application {application_id} is now in status: {status}.\n"
            f"Submission reference: {submission_reference or 'N/A'}"
        )

        # In production this maps user_id to a verified email in the Users table.
        email_result = self.notifier.send_email(
            to_address=f"{user_id}@example.com",
            subject=subject,
            message=message,
        )
        return {"email_result": email_result, "status": status}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.notify_status(**kwargs)
