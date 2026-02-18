import uuid
from typing import Any

from automation.browser_controller import BrowserController
from backend.src.logger import get_logger
from backend.src.services.bedrock_client import BedrockClient

logger = get_logger(__name__)


class NovaActController:
    def __init__(self, bedrock: BedrockClient, browser_controller: BrowserController) -> None:
        self.bedrock = bedrock
        self.browser_controller = browser_controller

    def execute(
        self,
        *,
        application_id: str,
        target_url: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute real browser steps with screenshot artifacts."""
        logger.info("Starting automation for %s at %s", application_id, target_url)

        planned_steps = plan.get("steps") if isinstance(plan, dict) else None
        if not isinstance(planned_steps, list) or not planned_steps:
            planned_steps = [
                "Open target site",
                "Authenticate session",
                "Populate applicant details",
                "Upload required documents",
                "Review and submit",
            ]

        result = self.browser_controller.run(
            application_id=application_id,
            target_url=target_url,
            profile=profile,
            documents=documents,
            planned_steps=[str(step) for step in planned_steps],
        )

        if not result.get("submission_reference") and result.get("success"):
            result["submission_reference"] = f"SA-{application_id[:8]}-{uuid.uuid4().hex[:6]}"

        return result
