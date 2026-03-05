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

    def _invoke_converse(
        self,
        *,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        return self.runtime.converse(
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
        candidates = [model_id]
        if ":" not in model_id:
            candidates.append(f"{model_id}:0")

        response: dict[str, Any] | None = None
        last_error: Exception | None = None
        for candidate in candidates:
            try:
                response = self._invoke_converse(
                    model_id=candidate,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                break
            except (ClientError, BotoCoreError) as exc:
                last_error = exc
                if isinstance(exc, ClientError):
                    error = exc.response.get("Error", {})
                    message = str(error.get("Message", "")).lower()
                    code = str(error.get("Code", ""))
                    should_retry = code == "ValidationException" and "model identifier" in message
                    if should_retry and candidate != candidates[-1]:
                        logger.warning("Retrying Bedrock converse with alternate model id: %s", candidates[-1])
                        continue
                logger.exception("Bedrock converse call failed")
                break

        if response is None:
            return {"error": str(last_error) if last_error else "unknown_error", "raw_text": ""}

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
