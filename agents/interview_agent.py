import json
from typing import Any

from agents.base import Agent
from backend.src.services.bedrock_client import BedrockClient


class InterviewAgent(Agent):
    def __init__(self, bedrock: BedrockClient, model_id: str) -> None:
        self.bedrock = bedrock
        self.model_id = model_id

    @property
    def name(self) -> str:
        return "interview_agent"

    def collect_profile(
        self,
        *,
        application_type: str,
        interview_history: list[dict[str, Any]],
        current_profile: dict[str, Any],
    ) -> dict[str, Any]:
        history_text = json.dumps(interview_history[-12:], ensure_ascii=True)
        profile_text = json.dumps(current_profile, ensure_ascii=True)

        system_prompt = (
            "You are an administrative intake specialist. "
            "Collect complete applicant details for a bureaucratic process. "
            "Return JSON only with keys: profile, next_questions, confidence."
        )

        user_prompt = (
            f"Application type: {application_type}\n"
            f"Current profile JSON: {profile_text}\n"
            f"Interview history JSON: {history_text}\n"
            "Extract all known fields into profile and ask only high-value missing questions."
        )

        output = self.bedrock.converse_json(
            model_id=self.model_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        if "profile" in output:
            return {
                "profile": output.get("profile", {}),
                "next_questions": output.get("next_questions", []),
                "confidence": output.get("confidence", 0.0),
            }

        fallback_questions = [
            "What is your legal full name as shown on your ID?",
            "What is your current residential address?",
            "What is your date of birth?",
        ]
        return {
            "profile": current_profile,
            "next_questions": fallback_questions,
            "confidence": 0.2,
            "model_fallback": output,
        }

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.collect_profile(**kwargs)
