import json
from typing import Any

from agents.base import Agent
from backend.src.services.bedrock_client import BedrockClient


class PlannerAgent(Agent):
    def __init__(self, bedrock: BedrockClient, model_id: str) -> None:
        self.bedrock = bedrock
        self.model_id = model_id

    @property
    def name(self) -> str:
        return "planner_agent"

    def plan(
        self,
        *,
        user_goal: str,
        application_type: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        interview_history: list[dict[str, Any]],
        previous_tasks: list[dict[str, Any]],
        previous_agent_outputs: dict[str, Any],
        current_status: str,
        demo_mode: bool = False,
        demo_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        system_prompt = (
            "You are the central planning brain for a multi-agent administrative worker. "
            "Return JSON only with keys: goal, reasoning_summary, next_action, missing_requirements, clarification_questions, tasks. "
            "Each task must contain: step, action, status. "
            "Allowed next_action values: collect_user_info, collect_document, extract_document, validate_profile, automate_submission, goal_complete."
        )

        user_prompt = (
            f"User goal: {user_goal}\n"
            f"Application type: {application_type}\n"
            f"Current status: {current_status}\n"
            f"Profile JSON: {json.dumps(profile, ensure_ascii=True)}\n"
            f"Documents JSON: {json.dumps(documents, ensure_ascii=True)}\n"
            f"Interview JSON: {json.dumps(interview_history[-12:], ensure_ascii=True)}\n"
            f"Previous tasks JSON: {json.dumps(previous_tasks, ensure_ascii=True)}\n"
            f"Previous agent outputs JSON: {json.dumps(previous_agent_outputs, ensure_ascii=True)}\n"
            f"Demo mode: {json.dumps(demo_mode)}\n"
            f"Demo context JSON: {json.dumps(demo_context or {}, ensure_ascii=True)}\n"
            "Decide the next best action and produce an updated task list."
        )

        raw_plan = self.bedrock.converse_json(
            model_id=self.model_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=1800,
        )

        normalized = self._normalize_plan(
            raw_plan=raw_plan,
            user_goal=user_goal,
            application_type=application_type,
            profile=profile,
            documents=documents,
            previous_tasks=previous_tasks,
            previous_agent_outputs=previous_agent_outputs,
        )

        if demo_mode and isinstance(demo_context, dict):
            demo_plan = self._demo_plan(
                user_goal=user_goal,
                application_type=application_type,
                profile=profile,
                documents=documents,
                previous_tasks=previous_tasks,
                demo_context=demo_context,
            )
            demo_plan["model_raw"] = normalized.get("model_raw", raw_plan)
            return demo_plan

        return normalized

    def _demo_plan(
        self,
        *,
        user_goal: str,
        application_type: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        previous_tasks: list[dict[str, Any]],
        demo_context: dict[str, Any],
    ) -> dict[str, Any]:
        required_documents = demo_context.get("required_documents", [])
        if not isinstance(required_documents, list):
            required_documents = []

        profile_requirements = demo_context.get("required_profile_fields", [])
        if not isinstance(profile_requirements, list):
            profile_requirements = ["legal_name", "date_of_birth", "email", "address"]

        uploaded_labels: set[str] = set()
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            for field in ("document_type", "label", "file_name", "s3_key"):
                value = doc.get(field)
                if isinstance(value, str):
                    uploaded_labels.add(value.lower())

        missing_requirements = []
        for requirement in required_documents:
            req = str(requirement).lower()
            if any(req in label for label in uploaded_labels):
                continue
            missing_requirements.append(str(requirement))

        missing_profile_fields = [str(field) for field in profile_requirements if not profile.get(str(field))]
        unprocessed_docs_exist = any(doc.get("status") != "processed" for doc in documents if isinstance(doc, dict))

        if missing_profile_fields:
            next_action = "collect_user_info"
            reasoning = "Demo mode: capture the remaining scholarship applicant identity fields."
            clarification_questions = [f"Please provide your {field.replace('_', ' ')}." for field in missing_profile_fields]
        elif missing_requirements:
            next_action = "collect_document"
            reasoning = "Demo mode: required scholarship evidence documents are still missing."
            clarification_questions = [f"Please upload your {item.replace('_', ' ')}." for item in missing_requirements]
        elif unprocessed_docs_exist:
            next_action = "extract_document"
            reasoning = "Demo mode: process uploaded documents before submission."
            clarification_questions = []
        else:
            next_action = "automate_submission"
            reasoning = "Demo mode: all required information is available, proceed to automated submission."
            clarification_questions = []

        task_template = demo_context.get("task_template", [])
        tasks = previous_tasks
        if not tasks and isinstance(task_template, list):
            tasks = [
                {
                    "step": int(task.get("step", idx + 1)),
                    "action": str(task.get("action", "pending_action")),
                    "status": "pending",
                }
                for idx, task in enumerate(task_template)
                if isinstance(task, dict)
            ]

        task_status_overrides = {
            "collect_user_info": {"collect_user_info": "in_progress"},
            "collect_document": {"collect_user_info": "completed", "collect_document": "in_progress"},
            "extract_document": {
                "collect_user_info": "completed",
                "collect_document": "completed",
                "extract_document": "in_progress",
            },
            "automate_submission": {
                "collect_user_info": "completed",
                "collect_document": "completed",
                "extract_document": "completed",
                "validate_profile": "completed",
                "automate_submission": "in_progress",
            },
        }
        overrides = task_status_overrides.get(next_action, {})
        normalized_tasks: list[dict[str, Any]] = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            action = str(task.get("action", "pending_action"))
            normalized_tasks.append(
                {
                    "step": int(task.get("step", len(normalized_tasks) + 1)),
                    "action": action,
                    "status": overrides.get(action, task.get("status", "pending")),
                }
            )

        if not normalized_tasks:
            normalized_tasks = [
                {"step": 1, "action": "collect_user_info", "status": "pending"},
                {"step": 2, "action": "collect_document", "status": "pending"},
                {"step": 3, "action": "extract_document", "status": "pending"},
                {"step": 4, "action": "validate_profile", "status": "pending"},
                {"step": 5, "action": "automate_submission", "status": "pending"},
            ]

        return {
            "goal": str(demo_context.get("goal", user_goal)),
            "reasoning_summary": reasoning,
            "next_action": next_action,
            "missing_requirements": missing_requirements,
            "clarification_questions": clarification_questions,
            "tasks": normalized_tasks,
            "model_raw": {"source": "demo_knowledge_base"},
        }

    def _normalize_plan(
        self,
        *,
        raw_plan: dict[str, Any],
        user_goal: str,
        application_type: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        previous_tasks: list[dict[str, Any]],
        previous_agent_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(raw_plan.get("tasks"), list) and isinstance(raw_plan.get("next_action"), str):
            normalized_tasks = []
            for idx, task in enumerate(raw_plan.get("tasks", []), start=1):
                if not isinstance(task, dict):
                    continue
                normalized_tasks.append(
                    {
                        "step": int(task.get("step", idx)),
                        "action": str(task.get("action", "unknown")),
                        "status": str(task.get("status", "pending")),
                    }
                )

            return {
                "goal": str(raw_plan.get("goal", user_goal)),
                "reasoning_summary": str(raw_plan.get("reasoning_summary", "Planner generated next step from current state.")),
                "next_action": str(raw_plan.get("next_action", "collect_user_info")),
                "missing_requirements": [str(item) for item in raw_plan.get("missing_requirements", []) if isinstance(item, str)],
                "clarification_questions": [str(item) for item in raw_plan.get("clarification_questions", []) if isinstance(item, str)],
                "tasks": normalized_tasks or previous_tasks,
                "model_raw": raw_plan,
            }

        return self._fallback_plan(
            user_goal=user_goal,
            application_type=application_type,
            profile=profile,
            documents=documents,
            previous_tasks=previous_tasks,
            previous_agent_outputs=previous_agent_outputs,
            raw_plan=raw_plan,
        )

    def _fallback_plan(
        self,
        *,
        user_goal: str,
        application_type: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        previous_tasks: list[dict[str, Any]],
        previous_agent_outputs: dict[str, Any],
        raw_plan: dict[str, Any],
    ) -> dict[str, Any]:
        required_by_type = {
            "scholarship_application": ["passport", "academic_transcript"],
            "visa_application": ["passport"],
            "business_registration": ["government_id"],
        }

        required_documents = required_by_type.get(application_type, ["government_id"])
        uploaded_labels: set[str] = set()
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            for field in ("document_type", "label", "file_name", "s3_key"):
                value = doc.get(field)
                if isinstance(value, str):
                    uploaded_labels.add(value.lower())

        missing_requirements = []
        for requirement in required_documents:
            requirement_lower = requirement.lower()
            if any(requirement_lower in candidate for candidate in uploaded_labels):
                continue
            missing_requirements.append(requirement)

        required_profile_fields = ["legal_name", "date_of_birth", "address"]
        missing_profile_fields = [field for field in required_profile_fields if not profile.get(field)]

        automation_error = None
        if isinstance(previous_agent_outputs, dict):
            automation_payload = previous_agent_outputs.get("automation_agent")
            if isinstance(automation_payload, dict):
                automation_error = automation_payload.get("error")

        if automation_error:
            next_action = "collect_user_info"
            reasoning = "Automation failed; request clarification or corrections before retrying."
            clarification_questions = [
                "The automation step failed. Do you want to retry or provide corrected details?"
            ]
        elif missing_profile_fields:
            next_action = "collect_user_info"
            reasoning = "Core profile fields are missing; ask focused interview questions first."
            clarification_questions = [f"Please provide your {field.replace('_', ' ')}." for field in missing_profile_fields]
        elif missing_requirements:
            next_action = "collect_document"
            reasoning = "Required supporting documents are not yet available."
            clarification_questions = [f"Please upload your {item.replace('_', ' ')}." for item in missing_requirements]
        elif any(doc.get("status") != "processed" for doc in documents if isinstance(doc, dict)):
            next_action = "extract_document"
            reasoning = "At least one uploaded document is not yet processed."
            clarification_questions = []
        else:
            next_action = "validate_profile"
            reasoning = "Profile and documents are present; validate consistency before automation."
            clarification_questions = []

        tasks = previous_tasks or [
            {"step": 1, "action": "collect_user_info", "status": "pending"},
            {"step": 2, "action": "collect_document", "status": "pending"},
            {"step": 3, "action": "extract_document", "status": "pending"},
            {"step": 4, "action": "validate_profile", "status": "pending"},
            {"step": 5, "action": "automate_submission", "status": "pending"},
        ]

        return {
            "goal": user_goal,
            "reasoning_summary": reasoning,
            "next_action": next_action,
            "missing_requirements": missing_requirements,
            "clarification_questions": clarification_questions,
            "tasks": tasks,
            "model_raw": raw_plan,
        }

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.plan(**kwargs)
