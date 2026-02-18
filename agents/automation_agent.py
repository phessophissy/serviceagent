from typing import Any

from agents.base import Agent
from automation.nova_act_controller import NovaActController
from backend.src.services.bedrock_client import BedrockClient


class AutomationAgent(Agent):
    def __init__(
        self,
        bedrock: BedrockClient,
        controller: NovaActController,
        model_id: str,
    ) -> None:
        self.bedrock = bedrock
        self.controller = controller
        self.model_id = model_id

    @property
    def name(self) -> str:
        return "automation_agent"

    def submit_application(
        self,
        *,
        application_id: str,
        target_url: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        application_type: str,
    ) -> dict[str, Any]:
        plan_prompt = (
            "Create a browser automation plan for submitting this application. "
            "Return JSON only with keys: steps, risk_checks, expected_submission_proof."
        )
        plan_input = (
            f"Application ID: {application_id}\n"
            f"Type: {application_type}\n"
            f"Target URL: {target_url}\n"
            f"Profile fields: {profile}\n"
            f"Documents: {documents}"
        )

        plan = self.bedrock.converse_json(
            model_id=self.model_id,
            system_prompt=plan_prompt,
            user_prompt=plan_input,
            temperature=0.0,
            max_tokens=1600,
        )

        automation_result = self.controller.execute(
            application_id=application_id,
            target_url=target_url,
            profile=profile,
            documents=documents,
            plan=plan,
        )

        return {
            "success": automation_result["success"],
            "steps": automation_result["steps"],
            "timeline": automation_result.get("timeline", []),
            "submission_reference": automation_result.get("submission_reference"),
            "artifacts": automation_result.get("artifacts", {}),
            "error": automation_result.get("error"),
            "plan": plan,
        }

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.submit_application(**kwargs)
