from typing import Any

from agents.base import Agent
from backend.src.services.bedrock_client import BedrockClient


class DocumentAgent(Agent):
    def __init__(self, bedrock: BedrockClient, model_id: str) -> None:
        self.bedrock = bedrock
        self.model_id = model_id

    @property
    def name(self) -> str:
        return "document_agent"

    def extract_fields(
        self,
        *,
        application_type: str,
        document_s3_key: str,
        existing_profile: dict[str, Any],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are a multimodal document extraction agent. "
            "Return JSON only with keys: fields, document_type, confidence, notes."
        )
        user_prompt = (
            f"Application type: {application_type}\n"
            f"S3 document key: {document_s3_key}\n"
            f"Existing profile: {existing_profile}\n"
            "Infer likely fields from this document context and return structured extraction JSON."
        )

        output = self.bedrock.converse_json(
            model_id=self.model_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
        )

        if "fields" in output:
            return output

        return {
            "fields": {},
            "document_type": "unknown",
            "confidence": 0.1,
            "notes": [
                "Model output was not structured JSON.",
                "Document may require OCR pipeline or richer multimodal payload handling.",
            ],
            "model_fallback": output,
        }

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.extract_fields(**kwargs)
