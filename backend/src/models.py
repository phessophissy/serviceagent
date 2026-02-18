from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApplicationType(str, Enum):
    BUSINESS_REGISTRATION = "business_registration"
    SCHOOL_APPLICATION = "school_application"
    SCHOLARSHIP_APPLICATION = "scholarship_application"
    PASSPORT_APPLICATION = "passport_application"
    JOB_APPLICATION = "job_application"
    VISA_APPLICATION = "visa_application"


class DemoScenario(str, Enum):
    INTERNATIONAL_SCHOLARSHIP_APPLICATION = "international_scholarship_application"


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    NEEDS_USER_INPUT = "needs_user_input"
    READY_FOR_AUTOMATION = "ready_for_automation"
    SUBMITTED = "submitted"
    FAILED = "failed"


class CreateApplicationRequest(BaseModel):
    application_type: ApplicationType
    prompt: str = Field(min_length=3, max_length=1000)
    demo_mode: bool = False
    demo_scenario: DemoScenario | None = None


class CreateApplicationResponse(BaseModel):
    application_id: str
    status: ApplicationStatus
    next_questions: list[str]


class InterviewTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    transcript: str | None = None


class InterviewTurnResponse(BaseModel):
    status: ApplicationStatus
    extracted_profile: dict[str, Any]
    next_questions: list[str]


class RequestUploadUrlRequest(BaseModel):
    file_name: str
    content_type: str


class RequestUploadUrlResponse(BaseModel):
    document_id: str
    upload_url: str
    s3_key: str


class ProcessDocumentRequest(BaseModel):
    document_id: str
    s3_key: str


class ProcessDocumentResponse(BaseModel):
    extracted_fields: dict[str, Any]
    status: ApplicationStatus


class ValidateApplicationResponse(BaseModel):
    status: ApplicationStatus
    missing_fields: list[str]
    conflicts: list[str]
    clarification_questions: list[str]


class AutomationRunResponse(BaseModel):
    status: ApplicationStatus
    submission_reference: str | None
    automation_steps: list[str]


class PlannerStateResponse(BaseModel):
    application_id: str
    goal: str
    reasoning_summary: str
    next_action: str
    tasks: list[dict[str, Any]]
    missing_requirements: list[str]
    status: ApplicationStatus
    updated_at: str


class TimelineEntry(BaseModel):
    step: int
    action: str
    status: str
    timestamp: str
    screenshot_s3_key: str | None = None
    screenshot_url: str | None = None
    error: str | None = None


class ApplicationTimelineResponse(BaseModel):
    application_id: str
    timeline: list[TimelineEntry]


class ApplicationRecord(BaseModel):
    application_id: str
    user_id: str
    application_type: ApplicationType
    status: ApplicationStatus
    profile: dict[str, Any] = Field(default_factory=dict)
    interview_history: list[dict[str, Any]] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    automation_steps: list[str] = Field(default_factory=list)
    automation_timeline: list[dict[str, Any]] = Field(default_factory=list)
    submission_reference: str | None = None
    planner_goal: str = ""
    planner_reasoning: str = ""
    planner_next_action: str = ""
    planner_tasks: list[dict[str, Any]] = Field(default_factory=list)
    last_agent_outputs: dict[str, Any] = Field(default_factory=dict)
    demo_mode: bool = False
    demo_scenario: DemoScenario | None = None
    demo_context: dict[str, Any] = Field(default_factory=dict)
    target_url: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class AgentLogRecord(BaseModel):
    log_id: str
    application_id: str
    user_id: str
    agent_name: str
    level: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
