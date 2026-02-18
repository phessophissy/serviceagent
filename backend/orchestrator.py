import uuid
from datetime import datetime, timezone
from typing import Any

from agents.automation_agent import AutomationAgent
from agents.document_agent import DocumentAgent
from agents.interview_agent import InterviewAgent
from agents.notification_agent import NotificationAgent
from agents.planner_agent import PlannerAgent
from agents.validation_agent import ValidationAgent
from automation.browser_controller import BrowserController
from automation.nova_act_controller import NovaActController
from backend.src.config import settings
from backend.src.models import ApplicationRecord, ApplicationStatus, ApplicationType, DemoScenario
from backend.src.repositories.dynamodb_repository import DynamoRepository
from backend.src.services.bedrock_client import BedrockClient
from backend.src.services.notification_service import NotificationService
from backend.src.services.storage_service import StorageService


class ServiceAgentOrchestrator:
    def __init__(self) -> None:
        self.repo = DynamoRepository()
        self.storage = StorageService()
        self.notifications = NotificationService()
        self.browser_controller = BrowserController(self.storage)

        self.planner_agent = PlannerAgent(BedrockClient(), settings.nova_lite_model_id)
        self.interview_agent = InterviewAgent(BedrockClient(), settings.nova_sonic_model_id)
        self.document_agent = DocumentAgent(BedrockClient(), settings.nova_multimodal_model_id)
        self.validation_agent = ValidationAgent(BedrockClient(), settings.nova_lite_model_id)
        self.automation_agent = AutomationAgent(
            BedrockClient(),
            NovaActController(BedrockClient(), self.browser_controller),
            settings.nova_act_model_id,
        )
        self.notification_agent = NotificationAgent(self.notifications)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _assert_owner(self, application: dict[str, Any], user_id: str) -> None:
        if application.get("user_id") != user_id:
            raise PermissionError("User is not authorized for this application")

    @staticmethod
    def _merge_agent_output(application: dict[str, Any], agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        history = application.get("last_agent_outputs", {})
        if not isinstance(history, dict):
            history = {}
        history[agent_name] = payload
        return history

    @staticmethod
    def _default_target_url(application_type: str) -> str:
        if application_type == ApplicationType.SCHOLARSHIP_APPLICATION.value:
            return "https://example.org/demo-scholarship-form"
        return "https://example.org/demo-application-form"

    @staticmethod
    def _demo_knowledge_base(scenario: DemoScenario) -> dict[str, Any]:
        if scenario == DemoScenario.INTERNATIONAL_SCHOLARSHIP_APPLICATION:
            return {
                "goal": "Complete international scholarship application",
                "scenario": scenario.value,
                "target_url": "https://www.w3schools.com/html/html_forms.asp",
                "task_template": [
                    {"step": 1, "action": "collect_user_info"},
                    {"step": 2, "action": "collect_document"},
                    {"step": 3, "action": "extract_document"},
                    {"step": 4, "action": "validate_profile"},
                    {"step": 5, "action": "automate_submission"},
                ],
                "required_documents": ["passport", "academic_transcript"],
                "required_profile_fields": [
                    "legal_name",
                    "date_of_birth",
                    "email",
                    "address",
                    "nationality",
                    "intended_program",
                ],
                "starter_profile": {
                    "intended_program": "MSc Computer Science",
                    "nationality": "Nigerian",
                },
                "reasoning_guide": [
                    "Prioritize identity confirmation and travel document capture.",
                    "Require transcript before automation run.",
                    "Proceed to submission once required profile and documents are available.",
                ],
            }
        return {}

    def _next_goal(self, application: dict[str, Any], user_request: str | None) -> str:
        if user_request:
            return user_request
        if application.get("planner_goal"):
            return str(application["planner_goal"])
        app_type = str(application.get("application_type", "application"))
        return f"Complete a valid {app_type.replace('_', ' ')} submission"

    def _pick_unprocessed_document(self, application: dict[str, Any]) -> dict[str, Any] | None:
        for doc in application.get("documents", []):
            if isinstance(doc, dict) and doc.get("status") != "processed":
                return doc
        return None

    def _planner_state_update(self, plan: dict[str, Any], status: ApplicationStatus | str) -> dict[str, Any]:
        return {
            "planner_goal": plan.get("goal", ""),
            "planner_reasoning": plan.get("reasoning_summary", ""),
            "planner_next_action": plan.get("next_action", ""),
            "planner_tasks": plan.get("tasks", []),
            "missing_requirements": plan.get("missing_requirements", []),
            "clarification_questions": plan.get("clarification_questions", []),
            "status": status,
        }

    def _run_planning_loop(
        self,
        application_id: str,
        user_id: str,
        *,
        user_request: str | None = None,
        target_url: str | None = None,
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        for _ in range(max_iterations):
            app = self.repo.get_application(application_id)
            if not app:
                raise KeyError("Application not found")
            self._assert_owner(app, user_id)

            goal = self._next_goal(app, user_request)
            plan = self.planner_agent.plan(
                user_goal=goal,
                application_type=str(app.get("application_type", "")),
                profile=app.get("profile", {}),
                documents=app.get("documents", []),
                interview_history=app.get("interview_history", []),
                previous_tasks=app.get("planner_tasks", []),
                previous_agent_outputs=app.get("last_agent_outputs", {}),
                current_status=str(app.get("status", ApplicationStatus.IN_PROGRESS.value)),
                demo_mode=bool(app.get("demo_mode", False)),
                demo_context=app.get("demo_context", {}),
            )

            planned_state = self._planner_state_update(plan, app.get("status", ApplicationStatus.IN_PROGRESS))
            app = self.repo.update_application(application_id, planned_state)
            self.repo.append_agent_log(
                application_id,
                user_id,
                "planner_agent",
                "INFO",
                "Planner generated next action",
                {
                    "goal": plan.get("goal"),
                    "next_action": plan.get("next_action"),
                    "missing_requirements": plan.get("missing_requirements", []),
                },
            )

            next_action = str(plan.get("next_action", "collect_user_info"))

            if next_action == "collect_user_info":
                interview = self.interview_agent.collect_profile(
                    application_type=str(app.get("application_type", "")),
                    interview_history=app.get("interview_history", []),
                    current_profile=app.get("profile", {}),
                )
                questions = interview.get("next_questions", [])
                status = ApplicationStatus.NEEDS_USER_INPUT if questions else ApplicationStatus.IN_PROGRESS
                updates = {
                    "profile": interview.get("profile", app.get("profile", {})),
                    "clarification_questions": questions,
                    "status": status,
                    "last_agent_outputs": self._merge_agent_output(app, "interview_agent", interview),
                }
                app = self.repo.update_application(application_id, updates)
                self.repo.append_agent_log(application_id, user_id, "interview_agent", "INFO", "Interview collected data", interview)
                if status == ApplicationStatus.NEEDS_USER_INPUT:
                    return app
                continue

            if next_action == "collect_document":
                questions = plan.get("clarification_questions", [])
                if not questions:
                    missing = plan.get("missing_requirements", [])
                    if missing:
                        questions = [f"Please upload: {', '.join(missing)}"]
                updates = {
                    "status": ApplicationStatus.NEEDS_USER_INPUT,
                    "clarification_questions": questions,
                    "missing_requirements": plan.get("missing_requirements", []),
                    "last_agent_outputs": self._merge_agent_output(app, "planner_agent", plan),
                }
                return self.repo.update_application(application_id, updates)

            if next_action == "extract_document":
                doc = self._pick_unprocessed_document(app)
                if not doc:
                    updates = {
                        "status": ApplicationStatus.NEEDS_USER_INPUT,
                        "clarification_questions": ["Please upload required supporting documents."],
                        "last_agent_outputs": self._merge_agent_output(app, "planner_agent", plan),
                    }
                    return self.repo.update_application(application_id, updates)

                document_id = str(doc.get("document_id", ""))
                s3_key = str(doc.get("s3_key", ""))
                if not document_id or not s3_key:
                    return app

                extracted = self.document_agent.extract_fields(
                    application_type=str(app.get("application_type", "")),
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

                docs = app.get("documents", [])
                for item in docs:
                    if isinstance(item, dict) and item.get("document_id") == document_id:
                        item["status"] = "processed"
                        item["document_type"] = extracted.get("document_type", item.get("document_type"))

                merged_profile = {**app.get("profile", {}), **extracted.get("fields", {})}
                updates = {
                    "documents": docs,
                    "profile": merged_profile,
                    "status": ApplicationStatus.IN_PROGRESS,
                    "last_agent_outputs": self._merge_agent_output(app, "document_agent", extracted),
                }
                self.repo.append_agent_log(application_id, user_id, "document_agent", "INFO", "Document processed", extracted)
                self.repo.update_application(application_id, updates)
                continue

            if next_action == "validate_profile":
                validation = self.validation_agent.validate(
                    application_type=str(app.get("application_type", "")),
                    profile=app.get("profile", {}),
                    documents=app.get("documents", []),
                )
                needs_input = bool(validation.get("missing_fields") or validation.get("conflicts"))
                status = ApplicationStatus.NEEDS_USER_INPUT if needs_input else ApplicationStatus.READY_FOR_AUTOMATION
                updates = {
                    "missing_fields": validation.get("missing_fields", []),
                    "conflicts": validation.get("conflicts", []),
                    "clarification_questions": validation.get("clarification_questions", []),
                    "status": status,
                    "last_agent_outputs": self._merge_agent_output(app, "validation_agent", validation),
                }
                app = self.repo.update_application(application_id, updates)
                self.repo.append_agent_log(application_id, user_id, "validation_agent", "INFO", "Validation completed", validation)
                if needs_input:
                    return app
                continue

            if next_action == "automate_submission":
                url = target_url or str(app.get("target_url") or self._default_target_url(str(app.get("application_type", ""))))
                automation = self.automation_agent.submit_application(
                    application_id=application_id,
                    target_url=url,
                    profile=app.get("profile", {}),
                    documents=app.get("documents", []),
                    application_type=str(app.get("application_type", "")),
                )
                status = ApplicationStatus.SUBMITTED if automation.get("success") else ApplicationStatus.FAILED
                updates = {
                    "target_url": url,
                    "automation_steps": automation.get("steps", []),
                    "automation_timeline": automation.get("timeline", []),
                    "submission_reference": automation.get("submission_reference"),
                    "status": status,
                    "last_agent_outputs": self._merge_agent_output(app, "automation_agent", automation),
                }
                app = self.repo.update_application(application_id, updates)
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
                return app

            if next_action == "goal_complete":
                status = app.get("status", ApplicationStatus.READY_FOR_AUTOMATION)
                return self.repo.update_application(
                    application_id,
                    {
                        "status": status,
                        "last_agent_outputs": self._merge_agent_output(app, "planner_agent", plan),
                    },
                )

            self.repo.append_agent_log(
                application_id,
                user_id,
                "orchestrator",
                "WARNING",
                "Planner returned unknown action; waiting for user input",
                {"next_action": next_action},
            )
            return self.repo.update_application(
                application_id,
                {
                    "status": ApplicationStatus.NEEDS_USER_INPUT,
                    "clarification_questions": ["Please confirm how you want to proceed."],
                },
            )

        return self.repo.update_application(
            application_id,
            {
                "status": ApplicationStatus.NEEDS_USER_INPUT,
                "clarification_questions": ["Planner reached iteration limit. Please provide clarification."],
            },
        )

    def create_application(
        self,
        user_id: str,
        application_type: ApplicationType,
        prompt: str,
        demo_mode: bool = False,
        demo_scenario: DemoScenario | None = None,
    ) -> dict[str, Any]:
        app_id = str(uuid.uuid4())
        scenario = demo_scenario or (DemoScenario.INTERNATIONAL_SCHOLARSHIP_APPLICATION if demo_mode else None)
        demo_context = self._demo_knowledge_base(scenario) if scenario else {}
        starter_profile = demo_context.get("starter_profile", {}) if isinstance(demo_context, dict) else {}
        target_url = demo_context.get("target_url") if isinstance(demo_context, dict) else None

        record = ApplicationRecord(
            application_id=app_id,
            user_id=user_id,
            application_type=application_type,
            status=ApplicationStatus.IN_PROGRESS,
            interview_history=[{"role": "user", "message": prompt, "timestamp": self._now_iso()}],
            profile=starter_profile if isinstance(starter_profile, dict) else {},
            planner_goal=demo_context.get("goal", prompt) if isinstance(demo_context, dict) else prompt,
            demo_mode=demo_mode,
            demo_scenario=scenario,
            demo_context=demo_context if isinstance(demo_context, dict) else {},
            target_url=str(target_url) if target_url else None,
        ).model_dump(mode="json")

        self.repo.create_application(record)
        self.repo.append_agent_log(
            app_id,
            user_id,
            "orchestrator",
            "INFO",
            "Application created",
            {
                "application_type": application_type,
                "goal": prompt,
                "demo_mode": demo_mode,
                "demo_scenario": scenario.value if scenario else None,
            },
        )

        return self._run_planning_loop(app_id, user_id, user_request=prompt)

    def run_interview_turn(self, application_id: str, user_id: str, message: str, transcript: str | None) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        turn_text = transcript or message
        history = app.get("interview_history", [])
        history.append({"role": "user", "message": turn_text, "timestamp": self._now_iso()})
        self.repo.update_application(application_id, {"interview_history": history})

        return self._run_planning_loop(application_id, user_id, user_request=turn_text)

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
            "file_name": file_name,
            "s3_key": s3_key,
            "content_type": content_type,
            "status": "uploaded",
            "extracted_fields": {},
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }
        self.repo.create_document_record(doc_record)

        docs = app.get("documents", [])
        docs.append(
            {
                "document_id": document_id,
                "file_name": file_name,
                "s3_key": s3_key,
                "status": "uploaded",
            }
        )
        self.repo.update_application(application_id, {"documents": docs})

        self.repo.append_agent_log(
            application_id,
            user_id,
            "orchestrator",
            "INFO",
            "Upload URL generated",
            {"document_id": document_id, "s3_key": s3_key},
        )
        return {"document_id": document_id, "upload_url": upload_url, "s3_key": s3_key}

    def process_document(self, application_id: str, user_id: str, document_id: str, s3_key: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        extracted = self.document_agent.extract_fields(
            application_type=str(app.get("application_type", "")),
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

        docs = app.get("documents", [])
        for item in docs:
            if isinstance(item, dict) and item.get("document_id") == document_id:
                item["status"] = "processed"
                item["document_type"] = extracted.get("document_type", item.get("document_type"))

        merged_profile = {**app.get("profile", {}), **extracted.get("fields", {})}
        self.repo.update_application(
            application_id,
            {
                "documents": docs,
                "profile": merged_profile,
                "status": ApplicationStatus.IN_PROGRESS,
                "last_agent_outputs": self._merge_agent_output(app, "document_agent", extracted),
            },
        )

        self.repo.append_agent_log(application_id, user_id, "document_agent", "INFO", "Document extracted", extracted)
        return self._run_planning_loop(application_id, user_id, user_request="Document uploaded")

    def validate_application(self, application_id: str, user_id: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)

        validation = self.validation_agent.validate(
            application_type=str(app.get("application_type", "")),
            profile=app.get("profile", {}),
            documents=app.get("documents", []),
        )
        needs_input = bool(validation.get("missing_fields") or validation.get("conflicts"))
        status = ApplicationStatus.NEEDS_USER_INPUT if needs_input else ApplicationStatus.READY_FOR_AUTOMATION

        self.repo.update_application(
            application_id,
            {
                "missing_fields": validation.get("missing_fields", []),
                "conflicts": validation.get("conflicts", []),
                "clarification_questions": validation.get("clarification_questions", []),
                "status": status,
                "last_agent_outputs": self._merge_agent_output(app, "validation_agent", validation),
            },
        )

        self.repo.append_agent_log(application_id, user_id, "validation_agent", "INFO", "Validation completed", validation)
        if needs_input:
            return self.repo.get_application(application_id) or {}
        return self._run_planning_loop(application_id, user_id, user_request="Validation complete")

    def run_automation(self, application_id: str, user_id: str, target_url: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)
        return self._run_planning_loop(application_id, user_id, target_url=target_url)

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

    def get_planner_state(self, application_id: str, user_id: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)
        return {
            "application_id": application_id,
            "goal": app.get("planner_goal", ""),
            "reasoning_summary": app.get("planner_reasoning", ""),
            "next_action": app.get("planner_next_action", ""),
            "tasks": app.get("planner_tasks", []),
            "missing_requirements": app.get("missing_requirements", []),
            "status": app.get("status", ApplicationStatus.IN_PROGRESS),
            "updated_at": app.get("updated_at", self._now_iso()),
        }

    def get_timeline(self, application_id: str, user_id: str) -> dict[str, Any]:
        app = self.repo.get_application(application_id)
        if not app:
            raise KeyError("Application not found")
        self._assert_owner(app, user_id)
        raw_timeline = app.get("automation_timeline", [])
        timeline: list[dict[str, Any]] = []
        if isinstance(raw_timeline, list):
            for item in raw_timeline:
                if not isinstance(item, dict):
                    continue
                enriched = dict(item)
                key = enriched.get("screenshot_s3_key")
                if isinstance(key, str) and key:
                    try:
                        enriched["screenshot_url"] = self.storage.generate_download_url(
                            key,
                            bucket=settings.artifacts_bucket,
                        )
                    except Exception as exc:
                        enriched["artifact_error"] = str(exc)
                timeline.append(enriched)
        return {"application_id": application_id, "timeline": timeline}
