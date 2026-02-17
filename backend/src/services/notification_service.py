from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from backend.src.config import settings
from backend.src.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    def __init__(self) -> None:
        self.ses = boto3.client("sesv2", region_name=settings.aws_region)

    def send_email(self, to_address: str, subject: str, message: str) -> dict[str, Any]:
        if not settings.notification_sender_email:
            logger.info("Skipping SES email: sender not configured")
            return {"sent": False, "reason": "sender_not_configured"}

        try:
            response = self.ses.send_email(
                FromEmailAddress=settings.notification_sender_email,
                Destination={"ToAddresses": [to_address]},
                Content={
                    "Simple": {
                        "Subject": {"Data": subject},
                        "Body": {"Text": {"Data": message}},
                    }
                },
            )
            return {"sent": True, "message_id": response.get("MessageId")}
        except (ClientError, BotoCoreError) as exc:
            logger.exception("SES send_email failed")
            return {"sent": False, "reason": str(exc)}
