import base64
import json
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from backend.src.config import settings
from backend.src.logger import get_logger

logger = get_logger(__name__)


class NovaSonicStreamingService:
    """Bidirectional voice-turn helper using Nova Sonic through Bedrock runtime streaming."""

    def __init__(self) -> None:
        self.runtime = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        self.model_id = settings.nova_sonic_model_id

    @staticmethod
    def _audio_format(mime_type: str) -> str:
        normalized = (mime_type or "").lower()
        if "wav" in normalized:
            return "wav"
        if "mp3" in normalized or "mpeg" in normalized:
            return "mp3"
        if "webm" in normalized:
            return "webm"
        return "wav"

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return {}
        return {}

    def stream_turn(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        conversation_state: dict[str, Any],
    ) -> dict[str, Any]:
        if not audio_bytes:
            return {
                "user_transcript": "",
                "assistant_text": "I did not receive audio input. Please try again.",
                "assistant_audio_b64": "",
                "error": "empty_audio",
            }

        system_prompt = (
            "You are a real-time intake assistant for administrative applications. "
            "Return strict JSON with keys: user_transcript, assistant_reply. "
            "assistant_reply must be concise and request only the most relevant missing details."
        )

        user_prompt = (
            f"Current profile: {json.dumps(conversation_state.get('profile', {}), ensure_ascii=True)}\n"
            f"Pending requirements: {json.dumps(conversation_state.get('missing_requirements', []), ensure_ascii=True)}\n"
            f"Previous questions: {json.dumps(conversation_state.get('clarification_questions', []), ensure_ascii=True)}"
        )

        raw_text_parts: list[str] = []
        audio_chunks: list[bytes] = []

        try:
            response = self.runtime.converse_stream(
                modelId=self.model_id,
                system=[{"text": system_prompt}],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "audio": {
                                    "format": self._audio_format(mime_type),
                                    "source": {"bytes": audio_bytes},
                                }
                            },
                            {"text": user_prompt},
                        ],
                    }
                ],
                inferenceConfig={"temperature": 0.2, "maxTokens": 600},
            )

            stream = response.get("stream", [])
            for event in stream:
                delta = event.get("contentBlockDelta", {}).get("delta", {})
                text = delta.get("text")
                if text:
                    raw_text_parts.append(text)

                audio_delta = delta.get("audio")
                if isinstance(audio_delta, dict):
                    source = audio_delta.get("source", {})
                    audio_bytes_chunk = source.get("bytes")
                    if isinstance(audio_bytes_chunk, (bytes, bytearray)):
                        audio_chunks.append(bytes(audio_bytes_chunk))

            raw_text = "".join(raw_text_parts).strip()
            payload = self._extract_json(raw_text)

            assistant_audio_b64 = ""
            if audio_chunks:
                assistant_audio_b64 = base64.b64encode(b"".join(audio_chunks)).decode("ascii")

            return {
                "user_transcript": str(payload.get("user_transcript", "")),
                "assistant_text": str(payload.get("assistant_reply", raw_text or "I heard you. Please continue.")),
                "assistant_audio_b64": assistant_audio_b64,
                "raw_text": raw_text,
            }
        except (ClientError, BotoCoreError) as exc:
            logger.exception("Nova Sonic streaming failed")
            return {
                "user_transcript": "",
                "assistant_text": "I received your audio but could not process it right now. Please continue.",
                "assistant_audio_b64": "",
                "error": str(exc),
            }
