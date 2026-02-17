import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from backend.src.config import settings
from backend.src.logger import get_logger

logger = get_logger(__name__)


def _to_decimal(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_decimal(v) for v in value]
    return value


def _from_decimal(value: Any) -> Any:
    if isinstance(value, list):
        return [_from_decimal(v) for v in value]
    if isinstance(value, dict):
        return {k: _from_decimal(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


class DynamoRepository:
    def __init__(self) -> None:
        self.ddb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.users_table = self.ddb.Table(settings.users_table)
        self.applications_table = self.ddb.Table(settings.applications_table)
        self.extracted_docs_table = self.ddb.Table(settings.extracted_docs_table)
        self.agent_logs_table = self.ddb.Table(settings.agent_logs_table)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def put_user_if_absent(self, user_id: str) -> None:
        self.users_table.put_item(
            Item={
                "user_id": user_id,
                "created_at": self.now_iso(),
                "updated_at": self.now_iso(),
            },
            ConditionExpression="attribute_not_exists(user_id)",
        )

    def create_application(self, record: dict[str, Any]) -> None:
        self.applications_table.put_item(Item=_to_decimal(record))

    def get_application(self, application_id: str) -> dict[str, Any] | None:
        response = self.applications_table.get_item(Key={"application_id": application_id})
        item = response.get("Item")
        return _from_decimal(item) if item else None

    def update_application(self, application_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_application(application_id)
        if not current:
            raise KeyError(f"Application {application_id} not found")

        current.update(updates)
        current["updated_at"] = self.now_iso()
        self.applications_table.put_item(Item=_to_decimal(current))
        return current

    def create_document_record(self, document: dict[str, Any]) -> None:
        self.extracted_docs_table.put_item(Item=_to_decimal(document))

    def update_document_record(self, document_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        response = self.extracted_docs_table.get_item(Key={"document_id": document_id})
        item = response.get("Item")
        if not item:
            raise KeyError(f"Document {document_id} not found")
        parsed = _from_decimal(item)
        parsed.update(updates)
        parsed["updated_at"] = self.now_iso()
        self.extracted_docs_table.put_item(Item=_to_decimal(parsed))
        return parsed

    def get_document_record(self, document_id: str) -> dict[str, Any] | None:
        response = self.extracted_docs_table.get_item(Key={"document_id": document_id})
        item = response.get("Item")
        return _from_decimal(item) if item else None

    def append_agent_log(
        self,
        application_id: str,
        user_id: str,
        agent_name: str,
        level: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        log_id = str(uuid.uuid4())
        item = {
            "log_id": log_id,
            "application_id": application_id,
            "user_id": user_id,
            "agent_name": agent_name,
            "level": level,
            "message": message,
            "payload": payload or {},
            "created_at": self.now_iso(),
        }
        self.agent_logs_table.put_item(Item=_to_decimal(item))

    def list_agent_logs(self, application_id: str) -> list[dict[str, Any]]:
        response = self.agent_logs_table.query(
            IndexName="application_id-created_at-index",
            KeyConditionExpression=Key("application_id").eq(application_id),
            ScanIndexForward=True,
        )
        items = response.get("Items", [])
        return [_from_decimal(item) for item in items]
