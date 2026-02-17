from typing import Any

from agents.base import Agent
from backend.src.services.bedrock_client import BedrockClient


class ValidationAgent(Agent):
    def __init__(self, bedrock: BedrockClient, model_id: str) -> None:
        self.bedrock = bedrock
        self.model_id = model_id

    @property
    def name(self) -> str:
        return "validation_agent"

    def validate(
        self,
        *,
        application_type: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are a compliance validator for administrative applications. "
            "Return JSON with keys: missing_fields, conflicts, clarification_questions, readiness_score."
        )
        user_prompt = (
            f"Application type: {application_type}\n"
            f"Profile: {profile}\n"
            f"Documents: {documents}\n"
            "Identify missing and conflicting data and propose specific clarification questions."
        )

        output = self.bedrock.converse_json(
            model_id=self.model_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
        )

        if "missing_fields" in output:
            return {
                "missing_fields": output.get("missing_fields", []),
                "conflicts": output.get("conflicts", []),
                "clarification_questions": output.get("clarification_questions", []),
                "readiness_score": output.get("readiness_score", 0.0),
            }

        return {
            "missing_fields": ["legal_name", "date_of_birth"],
            "conflicts": [],
            "clarification_questions": [
                "Please confirm your legal name exactly as shown on your passport.",
                "Please confirm your date of birth in YYYY-MM-DD format.",
            ],
            "readiness_score": 0.2,
            "model_fallback": output,
        }

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.validate(**kwargs)
