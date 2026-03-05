#!/usr/bin/env python3
"""Create required AWS resources for local/service bootstrap.

This script is idempotent:
- Existing DynamoDB tables are reused.
- Existing S3 bucket is reused when owned by the caller.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.src.config import settings


def _table_exists(dynamodb_client: Any, table_name: str) -> bool:
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
            return False
        raise


def _ensure_table(dynamodb_client: Any, table_name: str, spec: dict[str, Any]) -> None:
    if _table_exists(dynamodb_client, table_name):
        print(f"[ok] DynamoDB table exists: {table_name}")
        return

    payload = dict(spec)
    payload["TableName"] = table_name
    dynamodb_client.create_table(**payload)
    dynamodb_client.get_waiter("table_exists").wait(TableName=table_name)
    print(f"[created] DynamoDB table: {table_name}")


def _ensure_bucket(s3_client: Any, bucket_name: str, region: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"[ok] S3 bucket exists: {bucket_name}")
        return
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in ("404", "NoSuchBucket", "NotFound"):
            # AccessDenied can occur for an existing bucket owned by another account.
            if code in ("403", "AccessDenied"):
                raise RuntimeError(
                    f"S3 bucket '{bucket_name}' exists but is not accessible from this account."
                ) from exc
            raise

    params: dict[str, Any] = {"Bucket": bucket_name}
    if region != "us-east-1":
        params["CreateBucketConfiguration"] = {"LocationConstraint": region}

    try:
        s3_client.create_bucket(**params)
        print(f"[created] S3 bucket: {bucket_name}")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("BucketAlreadyOwnedByYou",):
            print(f"[ok] S3 bucket exists: {bucket_name}")
            return
        if code in ("BucketAlreadyExists",):
            raise RuntimeError(
                f"S3 bucket '{bucket_name}' is globally taken. "
                "Set S3_BUCKET to a unique name in your .env."
            ) from exc
        raise


def bootstrap() -> None:
    region = settings.aws_region
    dynamodb_client = boto3.client("dynamodb", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    table_specs: dict[str, dict[str, Any]] = {
        settings.users_table: {
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [{"AttributeName": "user_id", "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
        },
        settings.applications_table: {
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [{"AttributeName": "application_id", "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": "application_id", "KeyType": "HASH"}],
        },
        settings.extracted_docs_table: {
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [{"AttributeName": "document_id", "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": "document_id", "KeyType": "HASH"}],
        },
        settings.agent_logs_table: {
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "log_id", "AttributeType": "S"},
                {"AttributeName": "application_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
            ],
            "KeySchema": [{"AttributeName": "log_id", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "application_id-created_at-index",
                    "KeySchema": [
                        {"AttributeName": "application_id", "KeyType": "HASH"},
                        {"AttributeName": "created_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        },
        settings.planner_state_table: {
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [{"AttributeName": "application_id", "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": "application_id", "KeyType": "HASH"}],
        },
        settings.automation_timeline_table: {
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "application_id", "AttributeType": "S"},
                {"AttributeName": "step_number", "AttributeType": "N"},
            ],
            "KeySchema": [
                {"AttributeName": "application_id", "KeyType": "HASH"},
                {"AttributeName": "step_number", "KeyType": "RANGE"},
            ],
        },
    }

    print(f"Bootstrapping AWS resources in region: {region}")
    for table_name, spec in table_specs.items():
        _ensure_table(dynamodb_client, table_name, spec)

    _ensure_bucket(s3_client, settings.s3_bucket, region)
    if settings.documents_bucket != settings.s3_bucket:
        _ensure_bucket(s3_client, settings.documents_bucket, region)
    if settings.artifacts_bucket not in (settings.s3_bucket, settings.documents_bucket):
        _ensure_bucket(s3_client, settings.artifacts_bucket, region)

    print("Bootstrap complete.")


if __name__ == "__main__":
    bootstrap()
