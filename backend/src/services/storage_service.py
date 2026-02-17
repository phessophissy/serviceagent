import json
from datetime import datetime, timezone

import boto3

from backend.src.config import settings


class StorageService:
    def __init__(self) -> None:
        self.s3 = boto3.client("s3", region_name=settings.aws_region)
        self.bucket = settings.documents_bucket

    @staticmethod
    def now_prefix() -> str:
        return datetime.now(timezone.utc).strftime("%Y/%m/%d")

    def build_document_key(self, user_id: str, application_id: str, file_name: str) -> str:
        return f"documents/{self.now_prefix()}/{user_id}/{application_id}/{file_name}"

    def create_upload_url(self, s3_key: str, content_type: str) -> str:
        return self.s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=900,
        )

    def write_extracted_json(self, key: str, payload: dict) -> None:
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )

    def generate_download_url(self, s3_key: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=900,
        )
