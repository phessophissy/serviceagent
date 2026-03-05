import asyncio
import base64
import json
from typing import Annotated

import boto3
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from mangum import Mangum
from botocore.exceptions import BotoCoreError, ClientError

from backend.src.config import settings
from backend.src.models import (
    ApplicationTimelineResponse,
    ApplicationRecord,
    AutomationRunResponse,
    CreateApplicationRequest,
    CreateApplicationResponse,
    InterviewTurnRequest,
    InterviewTurnResponse,
    PlannerStateResponse,
    ProcessDocumentRequest,
    ProcessDocumentResponse,
    RequestUploadUrlRequest,
    RequestUploadUrlResponse,
    ValidateApplicationResponse,
)
from backend.orchestrator import ServiceAgentOrchestrator
from backend.src.services.sonic_streaming_service import NovaSonicStreamingService

app = FastAPI(title="Service Agent API", version="0.1.0")
orchestrator = ServiceAgentOrchestrator()
sonic_service = NovaSonicStreamingService()


def get_user_sub(x_user_sub: Annotated[str | None, Header()] = None) -> str:
    # In production, this should be mapped from Cognito authorizer claims.
    return x_user_sub or "demo-user"


def _check_aws_services() -> dict[str, bool]:
    services = {"dynamodb": False, "s3": False, "bedrock": False}

    try:
        dynamodb = boto3.client("dynamodb", region_name=settings.aws_region)
        dynamodb.list_tables(Limit=1)
        services["dynamodb"] = True
    except (ClientError, BotoCoreError):
        services["dynamodb"] = False

    try:
        s3 = boto3.client("s3", region_name=settings.aws_region)
        s3.list_buckets()
        services["s3"] = True
    except (ClientError, BotoCoreError):
        services["s3"] = False

    try:
        bedrock = boto3.client("bedrock", region_name=settings.aws_region)
        bedrock.list_foundation_models()
        services["bedrock"] = True
    except (ClientError, BotoCoreError):
        services["bedrock"] = False

    return services


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "services": _check_aws_services()}


@app.post("/applications", response_model=CreateApplicationResponse)
def create_application(request: CreateApplicationRequest, user_sub: str = Depends(get_user_sub)) -> CreateApplicationResponse:
    created = orchestrator.create_application(
        user_sub,
        request.application_type,
        request.prompt,
        request.demo_mode,
        request.demo_scenario,
    )
    return CreateApplicationResponse(
        application_id=created["application_id"],
        status=created["status"],
        next_questions=created.get("clarification_questions", []),
    )


@app.post("/applications/{application_id}/interview-turn", response_model=InterviewTurnResponse)
def interview_turn(
    application_id: str,
    request: InterviewTurnRequest,
    user_sub: str = Depends(get_user_sub),
) -> InterviewTurnResponse:
    try:
        updated = orchestrator.run_interview_turn(application_id, user_sub, request.message, request.transcript)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return InterviewTurnResponse(
        status=updated["status"],
        extracted_profile=updated.get("profile", {}),
        next_questions=updated.get("clarification_questions", []),
    )


@app.post("/applications/{application_id}/documents/upload-url", response_model=RequestUploadUrlResponse)
def request_upload_url(
    application_id: str,
    request: RequestUploadUrlRequest,
    user_sub: str = Depends(get_user_sub),
) -> RequestUploadUrlResponse:
    try:
        upload = orchestrator.request_upload_url(
            application_id=application_id,
            user_id=user_sub,
            file_name=request.file_name,
            content_type=request.content_type,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return RequestUploadUrlResponse(**upload)


@app.post("/applications/{application_id}/documents/process", response_model=ProcessDocumentResponse)
def process_document(
    application_id: str,
    request: ProcessDocumentRequest,
    user_sub: str = Depends(get_user_sub),
) -> ProcessDocumentResponse:
    try:
        updated = orchestrator.process_document(
            application_id=application_id,
            user_id=user_sub,
            document_id=request.document_id,
            s3_key=request.s3_key,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return ProcessDocumentResponse(
        extracted_fields=updated.get("profile", {}),
        status=updated["status"],
    )


@app.post("/applications/{application_id}/validate", response_model=ValidateApplicationResponse)
def validate_application(application_id: str, user_sub: str = Depends(get_user_sub)) -> ValidateApplicationResponse:
    try:
        updated = orchestrator.validate_application(application_id, user_sub)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return ValidateApplicationResponse(
        status=updated["status"],
        missing_fields=updated.get("missing_fields", []),
        conflicts=updated.get("conflicts", []),
        clarification_questions=updated.get("clarification_questions", []),
    )


@app.post("/applications/{application_id}/automate", response_model=AutomationRunResponse)
def run_automation(
    application_id: str,
    target_url: str,
    user_sub: str = Depends(get_user_sub),
) -> AutomationRunResponse:
    try:
        updated = orchestrator.run_automation(application_id, user_sub, target_url)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return AutomationRunResponse(
        status=updated["status"],
        submission_reference=updated.get("submission_reference"),
        automation_steps=updated.get("automation_steps", []),
    )


@app.get("/applications/{application_id}", response_model=ApplicationRecord)
def get_application(application_id: str, user_sub: str = Depends(get_user_sub)) -> ApplicationRecord:
    try:
        app_record = orchestrator.get_application(application_id, user_sub)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ApplicationRecord(**app_record)


@app.get("/applications/{application_id}/logs")
def get_logs(application_id: str, user_sub: str = Depends(get_user_sub)) -> dict:
    try:
        logs = orchestrator.list_logs(application_id, user_sub)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"logs": logs}


@app.get("/applications/{application_id}/timeline", response_model=ApplicationTimelineResponse)
def get_timeline(application_id: str, user_sub: str = Depends(get_user_sub)) -> ApplicationTimelineResponse:
    try:
        timeline = orchestrator.get_timeline(application_id, user_sub)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ApplicationTimelineResponse(**timeline)


@app.get("/planner/state/{application_id}", response_model=PlannerStateResponse)
def get_planner_state(application_id: str, user_sub: str = Depends(get_user_sub)) -> PlannerStateResponse:
    try:
        state = orchestrator.get_planner_state(application_id, user_sub)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return PlannerStateResponse(**state)


@app.websocket("/ws/interview/{application_id}")
async def interview_stream(websocket: WebSocket, application_id: str) -> None:
    await websocket.accept()
    user_sub = websocket.query_params.get("x_user_sub", "demo-user")

    buffered_chunks: list[bytes] = []
    mime_type = "audio/webm"

    async def process_buffer() -> None:
        if not buffered_chunks:
            return

        audio_payload = b"".join(buffered_chunks)
        buffered_chunks.clear()

        try:
            app_state = orchestrator.get_application(application_id, user_sub)
        except (KeyError, PermissionError):
            await websocket.send_json({"type": "error", "message": "Application access denied"})
            return

        voice_response = await asyncio.to_thread(
            sonic_service.stream_turn,
            audio_bytes=audio_payload,
            mime_type=mime_type,
            conversation_state={
                "profile": app_state.get("profile", {}),
                "missing_requirements": app_state.get("missing_requirements", []),
                "clarification_questions": app_state.get("clarification_questions", []),
            },
        )

        transcript = str(voice_response.get("user_transcript", "")).strip()
        updated = app_state
        if transcript:
            try:
                updated = await asyncio.to_thread(
                    orchestrator.run_interview_turn,
                    application_id,
                    user_sub,
                    transcript,
                    transcript,
                )
            except (KeyError, PermissionError):
                await websocket.send_json({"type": "error", "message": "Failed to process interview turn"})
                return

        planner_state = await asyncio.to_thread(orchestrator.get_planner_state, application_id, user_sub)
        payload = {
            "type": "assistant_response",
            "assistant_text": voice_response.get("assistant_text", ""),
            "assistant_audio_b64": voice_response.get("assistant_audio_b64", ""),
            "assistant_audio_mime_type": "audio/wav",
            "user_transcript": transcript,
            "status": updated.get("status", "in_progress"),
            "next_questions": updated.get("clarification_questions", []),
            "missing_requirements": planner_state.get("missing_requirements", []),
            "goal": planner_state.get("goal", ""),
            "next_action": planner_state.get("next_action", ""),
            "current_step": planner_state.get("current_step", ""),
            "completed_steps": planner_state.get("completed_steps", []),
            "reasoning_summary": planner_state.get("reasoning_summary", ""),
        }
        await websocket.send_json(payload)

    try:
        await websocket.send_json({"type": "ready", "message": "Voice interview session started"})
        while True:
            raw_message = await websocket.receive_text()
            event = json.loads(raw_message)
            event_type = event.get("type")

            if event_type == "start":
                mime_type = str(event.get("mime_type", "audio/webm"))
                await websocket.send_json({"type": "ack", "message": "stream_started"})
                continue

            if event_type == "audio_chunk":
                mime_type = str(event.get("mime_type", mime_type))
                audio_b64 = str(event.get("audio_b64", ""))
                if audio_b64:
                    try:
                        buffered_chunks.append(base64.b64decode(audio_b64))
                    except Exception:
                        await websocket.send_json({"type": "error", "message": "Invalid audio chunk encoding"})
                        continue
                if len(buffered_chunks) >= 4:
                    await process_buffer()
                continue

            if event_type == "stop":
                await process_buffer()
                await websocket.send_json({"type": "session_stopped"})
                break

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            await websocket.send_json({"type": "error", "message": f"Unsupported event type: {event_type}"})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})


handler = Mangum(app)
