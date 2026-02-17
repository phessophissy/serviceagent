from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from mangum import Mangum

from backend.src.models import (
    ApplicationRecord,
    AutomationRunResponse,
    CreateApplicationRequest,
    CreateApplicationResponse,
    InterviewTurnRequest,
    InterviewTurnResponse,
    ProcessDocumentRequest,
    ProcessDocumentResponse,
    RequestUploadUrlRequest,
    RequestUploadUrlResponse,
    ValidateApplicationResponse,
)
from backend.src.services.orchestrator import ServiceAgentOrchestrator

app = FastAPI(title="Service Agent API", version="0.1.0")
orchestrator = ServiceAgentOrchestrator()


def get_user_sub(x_user_sub: Annotated[str | None, Header()] = None) -> str:
    # In production, this should be mapped from Cognito authorizer claims.
    return x_user_sub or "demo-user"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/applications", response_model=CreateApplicationResponse)
def create_application(request: CreateApplicationRequest, user_sub: str = Depends(get_user_sub)) -> CreateApplicationResponse:
    created = orchestrator.create_application(user_sub, request.application_type, request.prompt)
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


handler = Mangum(app)
