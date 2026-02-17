import uuid
from datetime import datetime, timezone
from typing import Any

from agents.automation_agent import AutomationAgent
from agents.document_agent import DocumentAgent
from agents.interview_agent import InterviewAgent
from agents.notification_agent import NotificationAgent
from agents.validation_agent import ValidationAgent
from automation.nova_act_controller import NovaActController
from backend.src.config import settings
from backend.src.models import ApplicationRecord, ApplicationStatus, ApplicationType
from backend.src.repositories.dynamodb_repository import DynamoRepository
from backend.src.services.bedrock_client import BedrockClient
from backend.src.services.notification_service import NotificationService
from backend.src.services.storage_service import StorageService


class ServiceAgentOrchestrator:
    def __init__(self) -> None:
        self.repo = DynamoRepository()
        self.storage = StorageService()
        self.bedrock = BedrockClient()
        self.notifications = NotificationService()
        self.automation_controller = NovaActController(self.bedrock)

        self.interview_agent = InterviewAgent(self.bedrock, settings.nova_sonic_model_id)
        self.document_agent = DocumentAgent(self.bedrock, settings.nova_multimodal_model_id)
        self.validation_agent = ValidationAgent(self.bedrock, settings.nova_lite_model_id)
        self.automation_agent = AutomationAgent(
            self.bedrock,
            self.automation_controller,
            settings.nova_act_model_id,
        )
        self.notification_agent = NotificationAgent(self.notifications)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _assert_owner(self, application: dict[str, Any], user_id: str) -> None:
        if application.get("user_id") != user_id:
            raise PermissionError("User is not authorized for this application")

    def create_application(self, user_id: str, application_type: ApplicationType, prompt: str) -> dict[str, Any]:
        app_id = str(uuid.uuid4())
        record = ApplicationRecord(
            application_id=app_id,
            user_id=user_id,
            application_type=application_type,
            status=ApplicationStatus.IN_PROGRESS,
            interview_history=[{"role": "user", "message": prompt, "timestamp": self._now_iso()}],
        ).model_dump()

        self.repo.create_application(record)
        self.repo.append_agent_log(
            app_id,
            user_id,
            "orchestrator",
            "INFO",
            "Application created",
            {"application_type": application_type},
        )

        interview = self.interview_agent.collect_profile(
            application_type=application_type,
            interview_history=record["interview_history"],
            current_profile=record.get("profile", {}),
        )

        updated = self.repo.update_application(
            app_id,
            {
                "profile": interview.get("profile", {}),
                "clarification_questions": interview.get("next_questions", []),
                "status": ApplicationStatus.NEEDS_USER_INPUT,
            },
        )

        self.repo.append_agent_log(
            app_id,
            user_id,
            "interview_agent",
            "INFO",
            "Initial interview processed",
            interview,
        )
        return updated

    def run_interview_turn(self, application_id: str, user_id: str, message: str, transcript: str | None) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        turn_text = transcript or message
        history = app.get("interview_history", [])
        history.append({"role": "user", "message": turn_text, "timestamp": self._now_iso()})

        interview = self.interview_agent.collect_profile(
            application_type=app["application_type"],
            interview_history=history,
            current_profile=app.get("profile", {}),
        )

        updated = self.repo.update_application(
            application_id,
            {
                "interview_history": history,
                "profile": interview.get("profile", app.get("profile", {})),
                "clarification_questions": interview.get("next_questions", []),
                "status": ApplicationStatus.NEEDS_USER_INPUT if interview.get("next_questions") else ApplicationStatus.IN_PROGRESS,
            },
        )

        self.repo.append_agent_log(
            application_id,
            user_id,
            "interview_agent",
            "INFO",
            "Interview turn processed",
            interview,
        )
        return updated

    def request_upload_url(
        self,
        application_id: str,
        user_id: str,
        file_name: str,
        content_type: str,
    ) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        document_id = str(uuid.uuid4())
        s3_key = self.storage.build_document_key(user_id, application_id, file_name)
        upload_url = self.storage.create_upload_url(s3_key, content_type)

        doc_record = {
            "document_id": document_id,
            "application_id": application_id,
            "user_id": user_id,
            "s3_key": s3_key,
            "content_type": content_type,
            "status": "uploaded",
            "extracted_fields": {},
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }
        self.repo.create_document_record(doc_record)

        docs = app.get("documents", [])
        docs.append({"document_id": document_id, "s3_key": s3_key, "status": "uploaded"})
        self.repo.update_application(application_id, {"documents": docs})

        return {"document_id": document_id, "upload_url": upload_url, "s3_key": s3_key}

    def process_document(self, application_id: str, user_id: str, document_id: str, s3_key: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        extracted = self.document_agent.extract_fields(
            application_type=app["application_type"],
            document_s3_key=s3_key,
            existing_profile=app.get("profile", {}),
        )

        extracted_key = f"extracted/{application_id}/{document_id}.json"
        self.storage.write_extracted_json(extracted_key, extracted)
        self.repo.update_document_record(
            document_id,
            {
                "status": "processed",
                "extracted_fields": extracted,
                "extracted_json_s3_key": extracted_key,
            },
        )

        merged_profile = {**app.get("profile", {}), **extracted.get("fields", {})}
        updated = self.repo.update_application(
            application_id,
            {
                "profile": merged_profile,
                "status": ApplicationStatus.IN_PROGRESS,
            },
        )

        self.repo.append_agent_log(
            application_id,
            user_id,
            "document_agent",
            "INFO",
            "Document extracted",
            extracted,
        )
        return updated

    def validate_application(self, application_id: str, user_id: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        result = self.validation_agent.validate(
            application_type=app["application_type"],
            profile=app.get("profile", {}),
            documents=app.get("documents", []),
        )

        status = ApplicationStatus.NEEDS_USER_INPUT if result["missing_fields"] or result["conflicts"] else ApplicationStatus.READY_FOR_AUTOMATION
        updated = self.repo.update_application(
            application_id,
            {
                "missing_fields": result["missing_fields"],
                "conflicts": result["conflicts"],
                "clarification_questions": result["clarification_questions"],
                "status": status,
            },
        )

        self.repo.append_agent_log(
            application_id,
            user_id,
            "validation_agent",
            "INFO",
            "Validation completed",
            result,
        )
        return updated

    def run_automation(self, application_id: str, user_id: str, target_url: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        automation = self.automation_agent.submit_application(
            application_id=application_id,
            target_url=target_url,
            profile=app.get("profile", {}),
            documents=app.get("documents", []),
            application_type=app["application_type"],
        )

        status = ApplicationStatus.SUBMITTED if automation.get("success") else ApplicationStatus.FAILED
        updated = self.repo.update_application(
            application_id,
            {
                "automation_steps": automation.get("steps", []),
                "submission_reference": automation.get("submission_reference"),
                "status": status,
            },
        )

        self.repo.append_agent_log(
            application_id,
            user_id,
            "automation_agent",
            "INFO" if automation.get("success") else "ERROR",
            "Automation run completed",
            automation,
        )

        self.notification_agent.notify_status(
            user_id=user_id,
            application_id=application_id,
            status=status,
            submission_reference=automation.get("submission_reference"),
        )

        self.repo.append_agent_log(
            application_id,
            user_id,
            "notification_agent",
            "INFO",
            "Notification sent",
            {"status": status},
        )

        return updated

    def get_application(self, application_id: str, user_id: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)
        return app

    def list_logs(self, application_id: str, user_id: str) -> list[dict[str, Any]]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)
        return self.repo.list_agent_logs(application_id)
