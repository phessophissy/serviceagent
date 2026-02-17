import json
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from backend.src.config import settings
from backend.src.logger import get_logger

logger = get_logger(__name__)


class BedrockClient:
    def __init__(self) -> None:
        self.runtime = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def converse_json(
        self,
        *,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        """Call Bedrock model and return parsed JSON when possible."""
        try:
            response = self.runtime.converse(
                modelId=model_id,
                system=[{"text": system_prompt}],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_prompt}],
                    }
                ],
                inferenceConfig={
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                },
            )
        except (ClientError, BotoCoreError) as exc:
            logger.exception("Bedrock converse call failed")
            return {"error": str(exc), "raw_text": ""}

        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])

        text_parts: list[str] = []
        for item in content:
            text = item.get("text")
            if text:
                text_parts.append(text)

        raw_text = "\n".join(text_parts).strip()
        if not raw_text:
            return {"error": "empty_response", "raw_text": ""}

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return {"raw_text": raw_text}
