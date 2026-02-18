import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.src.config import settings
from backend.src.logger import get_logger
from backend.src.services.storage_service import StorageService

try:
    from playwright.sync_api import Page, sync_playwright
except ImportError:  # pragma: no cover - runtime dependency in deployment image
    Page = Any  # type: ignore[assignment]
    sync_playwright = None

logger = get_logger(__name__)


class BrowserController:
    def __init__(self, storage: StorageService, headless: bool = True) -> None:
        self.storage = storage
        self.artifacts_bucket = settings.artifacts_bucket
        self.headless = headless

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _make_artifact_key(self, application_id: str, step_no: int) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"timeline/{application_id}/step_{step_no:02d}_{timestamp}.png"

    def _record_step(
        self,
        *,
        timeline: list[dict[str, Any]],
        application_id: str,
        action: str,
        status: str,
        page: Page | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        step_no = len(timeline) + 1
        entry: dict[str, Any] = {
            "step": step_no,
            "action": action,
            "status": status,
            "timestamp": self._now_iso(),
        }

        if error:
            entry["error"] = error

        if page is not None:
            try:
                screenshot = page.screenshot(full_page=True, type="png")
                key = self._make_artifact_key(application_id, step_no)
                self.storage.upload_artifact_bytes(key=key, body=screenshot, content_type="image/png")
                entry["screenshot_s3_key"] = key
                entry["screenshot_url"] = self.storage.generate_download_url(key, bucket=self.artifacts_bucket)
            except Exception as exc:  # pragma: no cover - best effort artifact capture
                logger.warning("Failed to capture screenshot for step %s: %s", action, exc)
                entry["artifact_error"] = str(exc)

        timeline.append(entry)
        return entry

    def _fill_field(self, page: Page, selectors: list[str], value: str) -> bool:
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                locator.first.click()
                locator.first.fill(value)
                return True
        return False

    def _fill_profile(self, page: Page, profile: dict[str, Any], timeline: list[dict[str, Any]], application_id: str) -> None:
        field_selectors = {
            "legal_name": [
                "input[name='legal_name']",
                "input[name='full_name']",
                "input[name*='name']",
                "input[id*='name']",
            ],
            "first_name": ["input[name='first_name']", "input[id*='first']"],
            "last_name": ["input[name='last_name']", "input[id*='last']"],
            "email": ["input[type='email']", "input[name*='email']"],
            "phone": ["input[type='tel']", "input[name*='phone']"],
            "date_of_birth": ["input[name*='birth']", "input[type='date']"],
            "address": ["input[name*='address']", "textarea[name*='address']"],
        }

        for key, value in profile.items():
            if value is None:
                continue
            string_value = str(value)
            selectors = field_selectors.get(
                key,
                [f"input[name='{key}']", f"textarea[name='{key}']", f"input[id*='{key.lower()}']"],
            )
            if self._fill_field(page, selectors, string_value):
                self._record_step(
                    timeline=timeline,
                    application_id=application_id,
                    action=f"fill_field:{key}",
                    status="completed",
                    page=page,
                )

    def _upload_documents(
        self,
        page: Page,
        documents: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        application_id: str,
    ) -> None:
        file_input = page.locator("input[type='file']")
        if file_input.count() == 0:
            self._record_step(
                timeline=timeline,
                application_id=application_id,
                action="upload_documents:skipped_no_file_input",
                status="completed",
                page=page,
            )
            return

        uploaded_any = False
        temporary_files: list[str] = []
        try:
            for document in documents:
                if not isinstance(document, dict):
                    continue

                local_path = document.get("local_path")
                if isinstance(local_path, str) and Path(local_path).exists():
                    file_input.first.set_input_files(local_path)
                    uploaded_any = True
                    self._record_step(
                        timeline=timeline,
                        application_id=application_id,
                        action=f"upload_document:{Path(local_path).name}",
                        status="completed",
                        page=page,
                    )
                    continue

                s3_key = document.get("s3_key")
                if isinstance(s3_key, str) and s3_key:
                    suffix = Path(s3_key).suffix or ".bin"
                    temp_path = self.storage.download_document_to_tempfile(s3_key=s3_key, suffix=suffix)
                    temporary_files.append(temp_path)
                    file_input.first.set_input_files(temp_path)
                    uploaded_any = True
                    self._record_step(
                        timeline=timeline,
                        application_id=application_id,
                        action=f"upload_document:{Path(s3_key).name}",
                        status="completed",
                        page=page,
                    )

            if not uploaded_any:
                self._record_step(
                    timeline=timeline,
                    application_id=application_id,
                    action="upload_documents:no_usable_documents",
                    status="completed",
                    page=page,
                )
        finally:
            for file_path in temporary_files:
                try:
                    Path(file_path).unlink(missing_ok=True)
                except Exception:  # pragma: no cover - best effort cleanup
                    pass

    def _submit_form(self, page: Page) -> bool:
        candidates = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')",
            "button:has-text('Continue')",
        ]
        for selector in candidates:
            locator = page.locator(selector)
            if locator.count() > 0:
                locator.first.click()
                return True
        return False

    def run(
        self,
        *,
        application_id: str,
        target_url: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        planned_steps: list[str],
    ) -> dict[str, Any]:
        timeline: list[dict[str, Any]] = []
        if sync_playwright is None:
            self._record_step(
                timeline=timeline,
                application_id=application_id,
                action="automation_unavailable",
                status="failed",
                error="Playwright is not installed in runtime",
            )
            return {
                "success": False,
                "steps": ["Automation runtime unavailable"],
                "timeline": timeline,
                "submission_reference": None,
                "error": "playwright_not_installed",
            }

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()

                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                self._record_step(
                    timeline=timeline,
                    application_id=application_id,
                    action="navigate_to_target",
                    status="completed",
                    page=page,
                )

                for step in planned_steps:
                    self._record_step(
                        timeline=timeline,
                        application_id=application_id,
                        action=f"planner_step:{step}",
                        status="completed",
                        page=page,
                    )

                self._fill_profile(page, profile, timeline, application_id)
                self._upload_documents(page, documents, timeline, application_id)

                submitted = self._submit_form(page)
                page.wait_for_timeout(1200)
                self._record_step(
                    timeline=timeline,
                    application_id=application_id,
                    action="submit_application" if submitted else "submit_application:button_not_found",
                    status="completed" if submitted else "failed",
                    page=page,
                )

                submission_reference = f"SA-{application_id[:8]}-{uuid.uuid4().hex[:6]}"
                browser.close()

                success = submitted
                return {
                    "success": success,
                    "steps": [entry.get("action", "") for entry in timeline],
                    "timeline": timeline,
                    "submission_reference": submission_reference if success else None,
                    "artifacts": {
                        "target_url": target_url,
                        "artifact_bucket": self.artifacts_bucket,
                        "timeline_steps": len(timeline),
                    },
                }
        except Exception as exc:
            logger.exception("Browser automation failed")
            self._record_step(
                timeline=timeline,
                application_id=application_id,
                action="automation_exception",
                status="failed",
                error=str(exc),
            )
            return {
                "success": False,
                "steps": [entry.get("action", "") for entry in timeline],
                "timeline": timeline,
                "submission_reference": None,
                "error": str(exc),
            }
